---
name: refactor
description: Restructure code without changing behavior. TRIGGER when the user asks to refactor, restructure, reorganize, extract, rename, or improve code architecture without changing functionality.
---
# Refactor

Restructure code to improve design, readability, and maintainability without changing external behavior.

## Steps

1. **Understand the current behavior** - Read the code and its tests. Run existing tests to establish a green baseline.
2. **Identify what to refactor** - Based on the user's request or code smells:
   - Long functions (>40 lines)
   - God classes doing too many things
   - Duplicated logic across modules
   - Tight coupling between components
   - Poor naming that obscures intent
   - Inconsistent patterns within the codebase
3. **Plan the refactoring** - Describe the changes before making them. Break large refactors into small, testable steps.
4. **Apply changes incrementally** - Make one refactoring move at a time. Run tests after each step.
5. **Verify behavior is preserved** - Run the full test suite. If no tests exist, verify manually and recommend adding tests.

## Common Refactoring Patterns

### Extract Function
```python
# Before: long function with mixed concerns
def process_order(order):
    # validate
    if not order.items:
        raise ValueError("Empty order")
    if order.total < 0:
        raise ValueError("Invalid total")
    # calculate tax
    tax = order.total * 0.08
    if order.state == "CA":
        tax = order.total * 0.0725
    # send notification
    send_email(order.customer, f"Order confirmed: ${order.total + tax}")
    return order.total + tax

# After: extracted into focused functions
def validate_order(order):
    if not order.items:
        raise ValueError("Empty order")
    if order.total < 0:
        raise ValueError("Invalid total")

def calculate_tax(total: float, state: str) -> float:
    rates = {"CA": 0.0725}
    return total * rates.get(state, 0.08)

def process_order(order):
    validate_order(order)
    tax = calculate_tax(order.total, order.state)
    send_email(order.customer, f"Order confirmed: ${order.total + tax}")
    return order.total + tax
```

### Extract Class
```python
# Before: one class with too many responsibilities
class UserManager:
    def create_user(self, data): ...
    def update_user(self, id, data): ...
    def send_welcome_email(self, user): ...
    def send_password_reset(self, user): ...
    def generate_report(self, filters): ...

# After: separated by responsibility
class UserRepository:
    def create(self, data): ...
    def update(self, id, data): ...

class UserNotifier:
    def send_welcome_email(self, user): ...
    def send_password_reset(self, user): ...

class UserReportGenerator:
    def generate(self, filters): ...
```

### Replace Conditional with Polymorphism
```python
# Before
def calculate_price(product):
    if product.type == "book":
        return product.base_price * 0.9
    elif product.type == "electronics":
        return product.base_price * 1.1
    elif product.type == "food":
        return product.base_price

# After
class PricingStrategy:
    def calculate(self, base_price: float) -> float:
        raise NotImplementedError

class BookPricing(PricingStrategy):
    def calculate(self, base_price):
        return base_price * 0.9

class ElectronicsPricing(PricingStrategy):
    def calculate(self, base_price):
        return base_price * 1.1

PRICING = {"book": BookPricing(), "electronics": ElectronicsPricing()}

def calculate_price(product):
    strategy = PRICING.get(product.type, PricingStrategy())
    return strategy.calculate(product.base_price)
```

### Rename for Clarity
```python
# Before
def proc(d, f):
    r = []
    for i in d:
        if f(i):
            r.append(i)
    return r

# After
def filter_items(items, predicate):
    return [item for item in items if predicate(item)]
```

## Rules

- ALWAYS run tests before and after refactoring to verify behavior is preserved
- Make small, incremental changes -- not one massive rewrite
- If there are no tests for the code being refactored, recommend adding tests first
- Do not change the public API unless the user explicitly asks for it
- Do not mix refactoring with feature changes or bug fixes in the same step
- Commit after each successful refactoring step if the changes are significant
- If a refactoring introduces complexity rather than reducing it, reconsider the approach
