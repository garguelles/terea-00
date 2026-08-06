# Architecture

## Overview

This project is a Django 6 API using:

- Django REST Framework
- PostgreSQL
- Django ORM
- Django migrations
- Package-by-feature organization
- Domain-driven boundaries
- Explicit service and selector layers
- A modular monolith structure

The architecture keeps Django conventions intact while separating:

- Business behavior
- Application workflows
- HTTP concerns
- Persistence concerns
- Cross-application integrations
- Reporting concerns

The primary building blocks are:

```text
Django app       = bounded context or major feature
Model            = persistence model plus entity-local behavior
Domain helper    = pure business policy or value object
Service          = command or application use case
Selector         = query or read use case
Serializer       = API input/output boundary
DRF view         = HTTP adapter
Integration      = cross-context adapter
composition.py   = optional dependency wiring
Reporting app    = cross-context read models
config/          = application-wide configuration and URL composition
```

The goal is not to recreate a framework-independent architecture inside Django. The goal is to preserve clear boundaries while continuing to use Django in the way it is designed.

---

## Recommended project structure

```text
my_api/
├── manage.py
│
├── config/
│   ├── __init__.py
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── local.py
│   │   ├── test.py
│   │   └── production.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
│
├── apps/
│   ├── customers/
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   ├── admin.py
│   │   ├── models.py
│   │   ├── domain.py
│   │   ├── services.py
│   │   ├── selectors.py
│   │   ├── exceptions.py
│   │   ├── migrations/
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── serializers.py
│   │   │   ├── views.py
│   │   │   ├── permissions.py
│   │   │   └── urls.py
│   │   └── tests/
│   │
│   ├── orders/
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   ├── admin.py
│   │   ├── models.py
│   │   ├── domain.py
│   │   ├── services.py
│   │   ├── selectors.py
│   │   ├── exceptions.py
│   │   ├── composition.py
│   │   ├── integrations/
│   │   │   ├── __init__.py
│   │   │   └── customers.py
│   │   ├── migrations/
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── serializers.py
│   │   │   ├── views.py
│   │   │   ├── permissions.py
│   │   │   └── urls.py
│   │   └── tests/
│   │
│   ├── merchants/
│   ├── products/
│   │
│   └── reporting/
│       ├── __init__.py
│       ├── apps.py
│       ├── selectors.py
│       ├── exceptions.py
│       ├── api/
│       │   ├── __init__.py
│       │   ├── serializers.py
│       │   ├── views.py
│       │   ├── permissions.py
│       │   └── urls.py
│       └── tests/
│
├── common/
│   ├── __init__.py
│   ├── pagination.py
│   ├── exceptions.py
│   ├── permissions.py
│   ├── types.py
│   └── testing/
│
├── pyproject.toml
└── README.md
```

Small applications do not need every file immediately. Add files and subpackages only when they have a concrete responsibility.

For example, a simple lookup-only app may begin with:

```text
apps/currencies/
├── apps.py
├── models.py
├── admin.py
├── migrations/
├── api/
└── tests/
```

---

## Dependency direction

The normal command flow is:

```text
DRF view
    ↓
Application service
    ↓
Django model and domain behavior
    ↓
Django ORM
```

The normal read flow is:

```text
DRF view
    ↓
Selector
    ↓
Django ORM
    ↓
Serializer
```

Cross-context command flow:

```text
Order service
    ↓
Order-defined interface
    ↑
Order integration adapter
    ↓
Customer selector or service
```

Cross-context reporting flow:

```text
Reporting API
    ↓
Reporting selector
    ↓
Read-only ORM query across applications
    ↓
Reporting projection
```

Business behavior should point inward toward models, domain policies, and services. HTTP and integration code should remain at the edge.

---

## Django applications as bounded contexts

A major bounded context or feature should normally be represented by one Django app.

Examples:

```text
customers
orders
products
merchants
payments
reporting
```

A Django app owns:

- Its models
- Its migrations
- Its admin configuration
- Its business behavior
- Its services
- Its selectors
- Its API endpoints
- Its permissions
- Its tests

A model in another app may reference an owned model through a foreign key. That database relationship does not grant permission to bypass the owning app's business operations.

For example:

```python
class Order(models.Model):
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.PROTECT,
        related_name="orders",
    )
```

This relationship is valid. However, the order application should not directly update customer state or recreate customer business rules.

---

## Models

Django models represent persistence and may also contain entity-local behavior.

Models are responsible for:

- Fields and database constraints
- Relationships
- Entity-local state transitions
- Entity-local invariants
- Small calculations derived from model state
- Custom QuerySets and managers closely tied to the model

Example:

```python
from django.core.exceptions import ValidationError
from django.db import models


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.PROTECT,
        related_name="orders",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    total_amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def cancel(self) -> None:
        if self.status == self.Status.COMPLETED:
            raise ValidationError(
                "A completed order cannot be cancelled."
            )

        self.status = self.Status.CANCELLED
```

Good model methods:

```text
order.cancel()
order.mark_completed()
customer.deactivate()
product.change_price()
merchant.activate()
```

Avoid putting large workflows involving multiple apps into one model method.

Models should not:

- Parse HTTP requests
- Return DRF responses
- Instantiate serializers
- Call remote APIs directly
- Coordinate large multi-model workflows
- Contain reporting-specific query orchestration

---

## Domain helpers

Use `domain.py` or a `domain/` package for pure business concepts that do not need ORM persistence.

Examples:

- Value objects
- Pricing policies
- Eligibility rules
- Money calculations
- Date ranges
- Pure validation
- Domain-specific types

Example:

```python
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True)
class OrderLineInput:
    product_id: UUID
    quantity: int
    unit_price: Decimal

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise ValueError(
                "Quantity must be greater than zero."
            )

        if self.unit_price < 0:
            raise ValueError(
                "Unit price cannot be negative."
            )

    @property
    def total(self) -> Decimal:
        return self.unit_price * self.quantity
```

If `domain.py` becomes large, convert it into a package:

```text
apps/orders/domain/
├── __init__.py
├── order_line.py
├── pricing.py
├── policies.py
└── types.py
```

Domain helpers should not import:

- DRF
- Django views
- Serializers
- Another application's models
- Infrastructure clients

Pure domain helpers may import Django-independent shared value objects when the meaning is truly shared.

---

## Services

Services represent commands and application use cases.

Examples:

```text
create_order()
cancel_order()
complete_order()
deactivate_customer()
change_product_price()
capture_payment()
```

Services are responsible for:

- Coordinating multi-model workflows
- Calling entity behavior
- Enforcing workflow-level rules
- Calling cross-context interfaces
- Defining transaction boundaries
- Translating low-level failures into application exceptions
- Returning models or explicit result types

Prefer a function for simple use cases:

```python
from django.db import transaction

from apps.orders.models import Order


@transaction.atomic
def cancel_order(*, order: Order) -> Order:
    order.cancel()
    order.save(update_fields=["status"])

    return order
```

Prefer a class when the use case has dependencies:

```python
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from django.db import transaction

from apps.orders.models import Order, OrderItem


@dataclass(frozen=True)
class CustomerEligibility:
    customer_id: UUID
    may_place_orders: bool


class CustomerReader(Protocol):
    def get_eligibility(
        self,
        *,
        customer_id: UUID,
    ) -> CustomerEligibility:
        ...


class CustomerCannotOrder(Exception):
    pass


class CreateOrder:
    def __init__(
        self,
        customer_reader: CustomerReader,
    ) -> None:
        self.customer_reader = customer_reader

    @transaction.atomic
    def execute(
        self,
        *,
        customer_id: UUID,
        items: list[dict],
    ) -> Order:
        eligibility = self.customer_reader.get_eligibility(
            customer_id=customer_id,
        )

        if not eligibility.may_place_orders:
            raise CustomerCannotOrder(
                "Customer is not allowed to place orders."
            )

        total_amount = sum(
            Decimal(str(item["unit_price"]))
            * item["quantity"]
            for item in items
        )

        order = Order.objects.create(
            customer_id=customer_id,
            total_amount=total_amount,
        )

        OrderItem.objects.bulk_create(
            [
                OrderItem(
                    order=order,
                    product_id=item["product_id"],
                    quantity=item["quantity"],
                    unit_price=item["unit_price"],
                )
                for item in items
            ]
        )

        return order
```

Services should not:

- Depend on DRF request or response objects
- Perform serializer validation
- Return HTTP status codes
- Build pagination responses
- Contain presentation logic

---

## Selectors

Selectors represent queries and read use cases.

Examples:

```text
get_order()
list_customer_orders()
get_customer_profile()
list_active_products()
get_merchant_summary()
```

Selectors are responsible for:

- QuerySet construction
- Read optimization
- `select_related()`
- `prefetch_related()`
- Filtering
- Ordering
- Read-only annotations
- Purpose-built read projections

Example:

```python
from uuid import UUID

from django.db.models import QuerySet

from apps.orders.models import Order


def get_order(*, order_id: UUID) -> Order:
    return (
        Order.objects
        .select_related(
            "customer",
            "merchant",
        )
        .prefetch_related(
            "items",
            "items__product",
        )
        .get(id=order_id)
    )


def list_customer_orders(
    *,
    customer_id: UUID,
) -> QuerySet[Order]:
    return (
        Order.objects
        .filter(customer_id=customer_id)
        .order_by("-created_at")
    )
```

Selectors should be read-only.

Selectors must not:

- Save models
- Delete models
- Trigger command workflows
- Send notifications
- Publish events
- Call payment or email services
- Change domain state

A selector may return:

- A model
- A QuerySet
- A dataclass projection
- A dictionary projection
- A tuple
- A typed result object

Return a purpose-built projection when the caller does not need a full model.

---

## DRF serializers

Serializers form the API input and output boundary.

Use serializers for:

- Required fields
- Type validation
- Format validation
- Length validation
- Range validation
- Request-level relationships between fields
- Output representation

Keep input and output serializers separate for nontrivial endpoints.

Example:

```python
from rest_framework import serializers

from apps.orders.models import Order


class OrderItemInputSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1)
    unit_price = serializers.DecimalField(
        max_digits=18,
        decimal_places=2,
        min_value=0,
    )


class CreateOrderInputSerializer(serializers.Serializer):
    customer_id = serializers.UUIDField()
    items = OrderItemInputSerializer(
        many=True,
        allow_empty=False,
    )


class OrderOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = [
            "id",
            "customer_id",
            "status",
            "total_amount",
            "created_at",
        ]
        read_only_fields = fields
```

Serializer validation should cover transport-level concerns.

Example transport-level rule:

```text
quantity must be a positive integer
```

Business-level rules belong in models, domain policies, or services.

Example business-level rule:

```text
a suspended customer may not place an order
```

Avoid putting complex application workflows in:

```text
Serializer.create()
Serializer.update()
Serializer.validate()
```

Simple CRUD serializers may use `create()` and `update()` when no meaningful workflow exists.

---

## DRF views and viewsets

DRF views are HTTP adapters.

A view should:

1. Authenticate the request.
2. Check permissions.
3. Validate request input.
4. Call a selector or service.
5. Serialize the result.
6. Return an HTTP response.

Example:

```python
from rest_framework import status, viewsets
from rest_framework.response import Response

from apps.orders.api.serializers import (
    CreateOrderInputSerializer,
    OrderOutputSerializer,
)
from apps.orders.composition import create_order
from apps.orders.exceptions import CustomerCannotOrder


class OrderViewSet(viewsets.ViewSet):
    def create(self, request):
        input_serializer = CreateOrderInputSerializer(
            data=request.data,
        )
        input_serializer.is_valid(raise_exception=True)

        try:
            order = create_order.execute(
                **input_serializer.validated_data,
            )
        except CustomerCannotOrder as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_409_CONFLICT,
            )

        output_serializer = OrderOutputSerializer(order)

        return Response(
            output_serializer.data,
            status=status.HTTP_201_CREATED,
        )
```

Views must not:

- Implement business rules
- Perform large ORM workflows
- Manage multi-step transactions
- Directly update another application's models
- Recreate selector logic
- Duplicate service behavior

For simple CRUD resources, `ModelViewSet` and `ModelSerializer` are acceptable.

For explicit workflows, prefer custom actions or dedicated endpoints backed by services:

```text
POST /orders/{id}/cancel/
POST /orders/{id}/complete/
POST /customers/{id}/deactivate/
```

---

## URL ownership

Each application owns its API routes.

Example:

```python
# apps/orders/api/urls.py

from rest_framework.routers import SimpleRouter

from apps.orders.api.views import OrderViewSet


router = SimpleRouter()
router.register(
    "orders",
    OrderViewSet,
    basename="order",
)

urlpatterns = router.urls
```

The root URL configuration composes the application APIs:

```python
# config/urls.py

from django.urls import include, path


urlpatterns = [
    path(
        "api/v1/",
        include("apps.customers.api.urls"),
    ),
    path(
        "api/v1/",
        include("apps.orders.api.urls"),
    ),
    path(
        "api/v1/",
        include("apps.products.api.urls"),
    ),
    path(
        "api/v1/reports/",
        include("apps.reporting.api.urls"),
    ),
]
```

Do not place all endpoint definitions in `config/urls.py`.

---

## Cross-context communication

A bounded context owns its business behavior.

For example:

- Customers owns customer status and eligibility
- Orders owns order creation and cancellation
- Products owns product availability and pricing
- Merchants owns merchant lifecycle behavior

A command-side workflow should not directly query another application's models when the answer depends on that application's business meaning.

Incorrect:

```python
# apps/orders/services.py

from apps.customers.models import Customer


def create_order(*, customer_id, items):
    customer = Customer.objects.get(id=customer_id)

    if customer.status != Customer.Status.ACTIVE:
        ...
```

This tightly couples the order application to customer persistence and customer business meaning.

Prefer a consumer-owned protocol.

```python
# apps/orders/services.py

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class CustomerEligibility:
    customer_id: UUID
    may_place_orders: bool


class CustomerReader(Protocol):
    def get_eligibility(
        self,
        *,
        customer_id: UUID,
    ) -> CustomerEligibility:
        ...
```

The order integration adapter may call the customer application's public query.

```python
# apps/orders/integrations/customers.py

from uuid import UUID

from apps.customers.selectors import get_order_eligibility
from apps.orders.services import CustomerEligibility


class DjangoCustomerReader:
    def get_eligibility(
        self,
        *,
        customer_id: UUID,
    ) -> CustomerEligibility:
        result = get_order_eligibility(
            customer_id=customer_id,
        )

        return CustomerEligibility(
            customer_id=result.customer_id,
            may_place_orders=result.may_place_orders,
        )
```

The customer application owns the underlying query.

```python
# apps/customers/selectors.py

from dataclasses import dataclass
from uuid import UUID

from apps.customers.models import Customer


@dataclass(frozen=True)
class OrderEligibility:
    customer_id: UUID
    may_place_orders: bool


def get_order_eligibility(
    *,
    customer_id: UUID,
) -> OrderEligibility:
    customer = (
        Customer.objects
        .only("id", "status")
        .get(id=customer_id)
    )

    return OrderEligibility(
        customer_id=customer.id,
        may_place_orders=(
            customer.status
            == Customer.Status.ACTIVE
        ),
    )
```

The flow is:

```text
Order service
    ↓
Order-defined CustomerReader
    ↑
Order customer integration adapter
    ↓
Customer selector
    ↓
Customer model and ORM
```

### Cross-context rules

1. The consuming application defines the protocol it needs.
2. Keep the protocol limited to the required information.
3. Put translation logic in an integration adapter.
4. Do not expose another application's internal model as the integration contract.
5. Do not call another application's manager or repository directly from command logic.
6. Use the provider application's service for commands.
7. Use the provider application's selector for reads.
8. Use events when immediate consistency is not required.

Not every cross-app model import is forbidden.

Valid examples include:

- Foreign key declarations
- Admin display
- Reporting
- Read-only infrastructure
- Carefully controlled framework integration

The important rule is:

> Do not bypass the owning application's business behavior during command execution.

---

## Composition

A Django app is already the primary feature module.

Do not add a separate composition object to every app by default.

Create `composition.py` only when an application has concrete dependencies to wire.

Example:

```python
# apps/orders/composition.py

from apps.orders.integrations.customers import (
    DjangoCustomerReader,
)
from apps.orders.services import CreateOrder


customer_reader = DjangoCustomerReader()

create_order = CreateOrder(
    customer_reader=customer_reader,
)
```

This is the equivalent of feature-level dependency composition.

`composition.py` may:

- Instantiate service classes
- Instantiate integration adapters
- Connect protocols to concrete implementations
- Expose constructed use cases to views or tasks

It must not contain:

- Business rules
- ORM workflows
- HTTP handling
- Serializer logic
- Database queries
- Transactions

Do not use `AppConfig.ready()` as a dependency injection container.

Use `ready()` narrowly for framework startup behavior such as signal registration.

Avoid performing database queries during app initialization.

---

## Repositories

Do not create repository classes around every Django model by default.

Avoid wrappers that only rename the ORM:

```python
class OrderRepository:
    def create(self, **kwargs):
        return Order.objects.create(**kwargs)

    def get(self, order_id):
        return Order.objects.get(id=order_id)
```

Prefer:

- Model methods
- QuerySets
- Managers
- Selectors
- Services

Introduce a repository or port only when it protects a real boundary.

Examples:

- Multiple persistence backends
- A non-Django datastore
- Remote storage
- An external API
- A complex infrastructure implementation
- A replaceable service dependency

The Django ORM is not an implementation detail that must always be hidden. It is a core part of Django's application model.

---

## Transactions

Transaction boundaries should normally surround complete application use cases.

Use `transaction.atomic()` in services.

Example:

```python
from django.db import transaction


@transaction.atomic
def complete_order(*, order):
    order.mark_completed()
    order.save(update_fields=["status"])

    create_invoice(order=order)
    publish_outbox_event(order=order)

    return order
```

Views should not manage transaction details unless the view itself is intentionally the full transaction boundary.

Avoid enabling request-wide transactions as a substitute for explicit service boundaries.

For concurrent updates, use appropriate locking:

```python
from django.db import transaction

from apps.orders.models import Order


@transaction.atomic
def capture_order(*, order_id):
    order = (
        Order.objects
        .select_for_update()
        .get(id=order_id)
    )

    order.capture()
    order.save(update_fields=["status"])

    return order
```

Transaction rules:

1. Place atomic boundaries around complete commands.
2. Keep transactions as short as reasonably possible.
3. Do not perform slow remote calls inside a database transaction when avoidable.
4. Use an outbox pattern when publishing events must be atomic with database changes.
5. Use `select_for_update()` when state transitions require row locking.
6. Do not hide transaction boundaries inside serializers.

---

## Events and asynchronous work

Use events when another application needs to react but an immediate result is not required.

Examples:

```text
OrderCompleted
CustomerDeactivated
PaymentCaptured
ProductPriceChanged
```

Possible consumers:

- Notifications
- Reporting projections
- Audit logging
- Search indexing
- Analytics

Events should represent facts that have already occurred.

Prefer:

```text
OrderCompleted
```

Avoid command-like event names:

```text
CompleteOrder
```

For production systems, use a transactional outbox when event publication must remain consistent with database writes.

Django signals should be used carefully.

Appropriate uses:

- Framework-level lifecycle integration
- Cache invalidation with limited impact
- Small local reactions
- Third-party package hooks

Avoid using signals for critical business workflows because the execution path becomes implicit and difficult to trace.

Prefer explicit service calls or explicit event publication for important behavior.

---

## Reporting and cross-context read models

A DDD aggregate is a transactional consistency boundary. It is not a reporting aggregation.

Reports commonly combine data owned by multiple applications:

- Customer yearly order count
- Merchant top-selling products
- Monthly revenue
- Product sales by category
- Customer purchase history

Implement cross-context reports in a dedicated reporting application.

```text
apps/reporting/
├── apps.py
├── selectors.py
├── exceptions.py
├── api/
│   ├── serializers.py
│   ├── views.py
│   ├── permissions.py
│   └── urls.py
└── tests/
```

The reporting application may not require models or a domain package when it only exposes read-only projections.

### Customer yearly orders

```python
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from django.db.models import Count, Sum
from django.db.models.functions import Coalesce

from apps.orders.models import Order


@dataclass(frozen=True)
class CustomerYearlyOrders:
    customer_id: UUID
    year: int
    order_count: int
    total_spent: Decimal


def get_customer_yearly_orders(
    *,
    customer_id: UUID,
    year: int,
) -> CustomerYearlyOrders:
    start = datetime(year, 1, 1)
    end = datetime(year + 1, 1, 1)

    result = (
        Order.objects
        .filter(
            customer_id=customer_id,
            created_at__gte=start,
            created_at__lt=end,
        )
        .aggregate(
            order_count=Count("id"),
            total_spent=Coalesce(
                Sum("total_amount"),
                Decimal("0"),
            ),
        )
    )

    return CustomerYearlyOrders(
        customer_id=customer_id,
        year=year,
        order_count=result["order_count"],
        total_spent=result["total_spent"],
    )
```

### Merchant top-selling products

```python
from django.db.models import (
    DecimalField,
    ExpressionWrapper,
    F,
    Sum,
)

from apps.orders.models import Order, OrderItem


def list_merchant_top_products(
    *,
    merchant_id,
    start_date,
    end_date,
    limit=10,
):
    line_revenue = ExpressionWrapper(
        F("quantity") * F("unit_price"),
        output_field=DecimalField(
            max_digits=18,
            decimal_places=2,
        ),
    )

    return (
        OrderItem.objects
        .filter(
            order__merchant_id=merchant_id,
            order__status=Order.Status.COMPLETED,
            order__created_at__gte=start_date,
            order__created_at__lt=end_date,
        )
        .values(
            "product_id",
            "product__name",
        )
        .annotate(
            quantity_sold=Sum("quantity"),
            revenue=Sum(line_revenue),
        )
        .order_by("-quantity_sold")[:limit]
    )
```

### Reporting rules

1. Reporting queries are read-only.
2. Reporting may import models from multiple applications.
3. Reporting returns projections, not writable domain entities.
4. Reporting must not update transactional models.
5. Reporting must not become a backdoor for commands.
6. Authorization must be checked before returning reports.
7. Avoid duplicating complex business semantics in query code.
8. Prefer aggregating stable facts written by the owning applications.
9. Optimize expensive reports with indexes, summary tables, materialized views, or event-driven projections.
10. Keep report queries in the reporting application.

Examples of stable reporting facts:

```text
completed_at
recognized_revenue
refunded_amount
sale_status
captured_amount
```

Do not infer critical business meaning from incomplete state when the owning application can persist an explicit fact.

---

## Permissions and authorization

Authentication belongs at the API boundary.

Authorization may exist at several layers:

- DRF permission classes
- Selector filters
- Service preconditions
- Model or domain policies

Use DRF permission classes for request-level access.

Examples:

```text
IsAuthenticated
IsMerchantMember
CanViewOrder
CanManageProduct
```

Use services for business authorization that is part of the use case.

Example:

```text
Only the owning merchant may cancel this order.
```

Selectors must filter data to the caller's permitted scope.

Avoid:

```python
Order.objects.get(id=order_id)
```

when ownership restrictions apply.

Prefer:

```python
Order.objects.get(
    id=order_id,
    merchant_id=actor.merchant_id,
)
```

Do not rely solely on object-level permission checks after loading unrestricted data.

Reporting endpoints must enforce the same ownership and tenancy boundaries as transactional endpoints.

---

## Exceptions and API error handling

Separate exception responsibilities:

- Domain exceptions represent violated business rules.
- Service exceptions represent use-case failures.
- ORM exceptions represent persistence failures.
- API exception handling maps known failures to HTTP responses.

Example application exceptions:

```python
class CustomerCannotOrder(Exception):
    pass


class OrderAlreadyCompleted(Exception):
    pass


class ProductUnavailable(Exception):
    pass
```

Map known exceptions through a central DRF exception handler or a small API translation layer.

Do not leak:

- Raw SQL errors
- Database constraint details
- Internal stack traces
- External provider payloads
- Sensitive identifiers

Use database constraints for integrity, but translate expected constraint failures into meaningful application errors where appropriate.

---

## Shared code

Use `common/` sparingly.

Good candidates:

- Pagination classes
- Base API exceptions
- Shared typing helpers
- Generic test helpers
- Generic permission utilities
- Truly universal value objects

Poor candidates:

- Order validation
- Customer status helpers
- Product-specific filtering
- Merchant-specific permissions
- Miscellaneous utility functions without ownership

A concept should remain in its owning application unless its meaning is genuinely shared.

Avoid creating a large generic `utils.py`.

Prefer small, named modules:

```text
common/pagination.py
common/dates.py
common/identifiers.py
common/testing/factories.py
```

---

## Migrations

Each application owns its migrations.

```text
apps/orders/migrations/
apps/customers/migrations/
apps/products/migrations/
```

Migration rules:

1. Keep schema changes in the owning app.
2. Review generated migrations before committing.
3. Use data migrations deliberately.
4. Avoid importing current model classes directly in migrations.
5. Use historical models through `apps.get_model()`.
6. Make large production migrations backward-compatible.
7. Separate destructive schema changes from application rollout when necessary.
8. Add indexes for known query patterns.
9. Verify reporting queries against realistic data volumes.
10. Do not edit already-applied migrations unless the repository policy explicitly allows it.

---

## Settings and configuration

Use environment-specific settings modules.

```text
config/settings/base.py
config/settings/local.py
config/settings/test.py
config/settings/production.py
```

`base.py` contains shared defaults.

Environment modules override only what differs.

Keep secrets in environment variables or a secrets manager.

Do not place business behavior in settings.

Register applications explicitly:

```python
INSTALLED_APPS = [
    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",

    # Third party
    "rest_framework",

    # Project
    "apps.customers.apps.CustomersConfig",
    "apps.orders.apps.OrdersConfig",
    "apps.products.apps.ProductsConfig",
    "apps.merchants.apps.MerchantsConfig",
    "apps.reporting.apps.ReportingConfig",
]
```

---

## Testing

### Model and domain tests

Test:

- Entity-local invariants
- State transitions
- Value objects
- Pure policies
- Database constraints
- Custom QuerySets and managers

Examples:

```text
completed orders cannot be cancelled
quantity must be positive
inactive products cannot be purchased
```

### Service tests

Test:

- Use-case orchestration
- Transactional behavior
- Cross-context interfaces
- Error handling
- Side effects
- Locking behavior

Use fakes for integration protocols when possible.

Example:

```python
class FakeCustomerReader:
    def __init__(self, *, may_place_orders):
        self.may_place_orders = may_place_orders

    def get_eligibility(self, *, customer_id):
        return CustomerEligibility(
            customer_id=customer_id,
            may_place_orders=self.may_place_orders,
        )
```

### Selector tests

Test:

- Filters
- Ordering
- Annotations
- Query counts
- Empty results
- Tenant scoping
- `select_related()` and `prefetch_related()` behavior

### API tests

Test:

- Authentication
- Permissions
- Input validation
- Status codes
- Error payloads
- Serialization
- Pagination
- Idempotency when relevant

### Reporting tests

Test:

- Date boundaries
- Time zones
- Empty datasets
- Refunds
- Cancellations
- Revenue semantics
- Authorization
- Aggregation accuracy
- Query performance

### End-to-end tests

Use selectively for critical flows through:

```text
HTTP
  ↓
Serializer
  ↓
Service
  ↓
Model and ORM
  ↓
PostgreSQL
```

---

## Adding a new application

When adding a new bounded context such as `payments`:

1. Create `apps/payments/`.
2. Add `apps.py`.
3. Add models and migrations.
4. Add entity-local behavior to models.
5. Add pure policies or value objects to `domain.py` when needed.
6. Add commands to `services.py`.
7. Add reads to `selectors.py`.
8. Add DRF serializers, views, permissions, and URLs under `api/`.
9. Add `composition.py` only when dependencies require wiring.
10. Register the app in `INSTALLED_APPS`.
11. Include its URLs from `config/urls.py`.
12. Add model, service, selector, and API tests.

---

## Adding a cross-context dependency

When application A needs business information or behavior from application B:

1. Define the required protocol in application A.
2. Keep the protocol limited to what A needs.
3. Add an integration adapter under A.
4. Call B's selector for reads.
5. Call B's service for commands.
6. Translate B's result into A's local type.
7. Wire the implementation in A's `composition.py`.
8. Test A's service with a fake implementation.
9. Do not expose B's internal model as the protocol contract.
10. Do not bypass B's business rules.

---

## Adding a cross-context report

When a report combines several applications:

1. Add the query to `apps/reporting/selectors.py`.
2. Define an explicit result projection when useful.
3. Use read-only ORM queries.
4. Add a reporting serializer.
5. Add a reporting view.
6. Add reporting permissions.
7. Register the reporting route.
8. Enforce tenant and ownership boundaries.
9. Add indexes for expensive filters and joins.
10. Test date boundaries and business semantics.
11. Introduce summary tables or materialized views when needed.
12. Do not perform transactional writes through reporting code.

---

## Core architecture rules

1. One major bounded context generally maps to one Django app.
2. Models and migrations remain inside their owning app.
3. Use model methods for entity-local behavior.
4. Use services for commands and multi-model workflows.
5. Use selectors for reads and QuerySet construction.
6. Keep DRF views thin.
7. Use serializers for API validation and representation.
8. Keep core business rules out of serializers and views.
9. Use the Django ORM directly unless a real boundary justifies a repository.
10. Keep transaction boundaries around complete service operations.
11. Do not use `AppConfig.ready()` as a dependency container.
12. Add `composition.py` only when concrete dependencies require wiring.
13. The consuming app defines cross-context protocols.
14. Cross-context translation belongs in an integration adapter.
15. Use provider selectors for reads and provider services for commands.
16. Do not bypass another app's business behavior.
17. Use events for asynchronous reactions.
18. Keep critical workflows explicit rather than hidden in signals.
19. Put cross-context read models in the reporting app.
20. Reporting queries must be read-only.
21. Reporting returns projections, not writable entities.
22. Apply authorization to both transactional and reporting endpoints.
23. Keep shared code small and intentional.
24. Keep Django conventions recognizable.
25. Prefer explicit, readable code over abstractions without a concrete purpose.

---

## Mental model

```text
Model
    = persistence and entity-local behavior

Domain helper
    = pure business policy or value object

Service
    = command or application use case

Selector
    = read use case and optimized ORM query

Serializer
    = API input and output boundary

DRF view
    = HTTP adapter

Integration
    = cross-context translation adapter

Django app
    = bounded context and primary feature module

composition.py
    = optional concrete dependency wiring

Reporting app
    = read-only cross-context projections

config/
    = application-wide settings and URL composition
```
