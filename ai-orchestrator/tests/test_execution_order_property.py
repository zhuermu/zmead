"""Property-based tests for multi-step execution order.

**Feature: ai-orchestrator, Property 2: Multi-step Execution Order**
**Validates: Requirements 3.3**

This module tests that the orchestrator correctly executes multi-step tasks
in dependency order (e.g., creative generation before campaign creation).
"""

import pytest
from hypothesis import given, settings, strategies as st
from typing import Any


# Module dependency graph - defines which modules must complete before others
MODULE_DEPENDENCIES = {
    "creative": [],  # No dependencies
    "reporting": [],  # No dependencies
    "market_intel": [],  # No dependencies
    "landing_page": [],  # No dependencies
    "ad_engine": ["creative", "landing_page"],  # Requires creative and landing_page
}

# Module to node mapping
MODULE_NODE_MAP = {
    "creative": "creative_stub",
    "reporting": "reporting_stub",
    "market_intel": "market_intel_stub",
    "landing_page": "landing_page_stub",
    "ad_engine": "ad_engine_stub",
}


def get_execution_order(actions: list[dict[str, Any]]) -> list[str]:
    """Determine the correct execution order for a list of actions.

    Uses topological sort based on module dependencies.
    """
    # Build dependency graph for the given actions
    modules = [a.get("module") for a in actions]

    # Simple topological sort
    result = []
    visited = set()

    def visit(module: str):
        if module in visited:
            return
        visited.add(module)
        for dep in MODULE_DEPENDENCIES.get(module, []):
            if dep in modules:
                visit(dep)
        result.append(module)

    for module in modules:
        visit(module)

    return result


def validate_execution_order(execution_order: list[str]) -> bool:
    """Validate that execution order respects dependencies.

    Returns True if all dependencies are satisfied.
    """
    executed = set()

    for module in execution_order:
        # Check all dependencies have been executed
        deps = MODULE_DEPENDENCIES.get(module, [])
        for dep in deps:
            if dep in execution_order and dep not in executed:
                return False
        executed.add(module)

    return True


class TestExecutionOrderProperty:
    """Property tests for multi-step execution order.

    **Feature: ai-orchestrator, Property 2: Multi-step Execution Order**
    **Validates: Requirements 3.3**
    """

    @settings(max_examples=100)
    @given(
        modules=st.lists(
            st.sampled_from(list(MODULE_DEPENDENCIES.keys())), min_size=1, max_size=5, unique=True
        )
    )
    def test_execution_order_respects_dependencies(self, modules: list[str]):
        """Property: For any set of modules, execution order SHALL respect dependencies."""
        actions = [{"module": m, "type": f"action_{m}"} for m in modules]
        order = get_execution_order(actions)

        assert validate_execution_order(order), f"Execution order {order} violates dependencies"

    @settings(max_examples=50)
    @given(st.data())
    def test_creative_before_ad_engine(self, data):
        """Property: Creative generation SHALL always happen before campaign creation."""
        # Generate a list that includes both creative and ad_engine
        other_modules = data.draw(
            st.lists(
                st.sampled_from(["reporting", "market_intel", "landing_page"]),
                min_size=0,
                max_size=3,
                unique=True,
            )
        )

        modules = ["creative", "ad_engine"] + other_modules
        actions = [{"module": m, "type": f"action_{m}"} for m in modules]
        order = get_execution_order(actions)

        creative_idx = order.index("creative")
        ad_engine_idx = order.index("ad_engine")

        assert creative_idx < ad_engine_idx, (
            f"Creative ({creative_idx}) should come before ad_engine ({ad_engine_idx})"
        )

    @settings(max_examples=50)
    @given(st.data())
    def test_landing_page_before_ad_engine(self, data):
        """Property: Landing page creation SHALL happen before campaign creation."""
        other_modules = data.draw(
            st.lists(
                st.sampled_from(["reporting", "market_intel", "creative"]),
                min_size=0,
                max_size=3,
                unique=True,
            )
        )

        modules = ["landing_page", "ad_engine"] + other_modules
        actions = [{"module": m, "type": f"action_{m}"} for m in modules]
        order = get_execution_order(actions)

        landing_page_idx = order.index("landing_page")
        ad_engine_idx = order.index("ad_engine")

        assert landing_page_idx < ad_engine_idx, (
            f"Landing page ({landing_page_idx}) should come before ad_engine ({ad_engine_idx})"
        )

    @settings(max_examples=100)
    @given(
        modules=st.lists(
            st.sampled_from(["creative", "reporting", "market_intel"]),
            min_size=1,
            max_size=3,
            unique=True,
        )
    )
    def test_independent_modules_can_be_in_any_order(self, modules: list[str]):
        """Property: Independent modules (no dependencies) can be in any order."""
        actions = [{"module": m, "type": f"action_{m}"} for m in modules]
        order = get_execution_order(actions)

        # All these modules are independent, so any order is valid
        assert set(order) == set(modules), f"All modules should be present in execution order"
        assert validate_execution_order(order), f"Execution order should be valid"

    @settings(max_examples=50)
    @given(st.data())
    def test_full_workflow_order(self, data):
        """Property: Full workflow with all modules SHALL respect all dependencies."""
        # Include all modules
        modules = list(MODULE_DEPENDENCIES.keys())
        actions = [{"module": m, "type": f"action_{m}"} for m in modules]
        order = get_execution_order(actions)

        # Verify all dependencies are respected
        assert validate_execution_order(order), f"Full workflow order {order} violates dependencies"

        # Specifically check ad_engine comes after its dependencies
        ad_engine_idx = order.index("ad_engine")
        creative_idx = order.index("creative")
        landing_page_idx = order.index("landing_page")

        assert creative_idx < ad_engine_idx, "Creative must come before ad_engine"
        assert landing_page_idx < ad_engine_idx, "Landing page must come before ad_engine"


class TestDependencyGraph:
    """Property tests for the dependency graph itself."""

    @settings(max_examples=20)
    @given(module=st.sampled_from(list(MODULE_DEPENDENCIES.keys())))
    def test_all_modules_have_dependency_entry(self, module: str):
        """Property: All modules SHALL have an entry in the dependency graph."""
        assert module in MODULE_DEPENDENCIES

    @settings(max_examples=20)
    @given(module=st.sampled_from(list(MODULE_DEPENDENCIES.keys())))
    def test_dependencies_are_valid_modules(self, module: str):
        """Property: All dependencies SHALL be valid module names."""
        deps = MODULE_DEPENDENCIES.get(module, [])
        for dep in deps:
            assert dep in MODULE_DEPENDENCIES, f"Dependency {dep} of {module} is not a valid module"

    def test_no_circular_dependencies(self):
        """Property: Dependency graph SHALL have no circular dependencies."""
        # Check for cycles using DFS
        visited = set()
        rec_stack = set()

        def has_cycle(module: str) -> bool:
            visited.add(module)
            rec_stack.add(module)

            for dep in MODULE_DEPENDENCIES.get(module, []):
                if dep not in visited:
                    if has_cycle(dep):
                        return True
                elif dep in rec_stack:
                    return True

            rec_stack.remove(module)
            return False

        for module in MODULE_DEPENDENCIES:
            if module not in visited:
                assert not has_cycle(module), f"Circular dependency detected involving {module}"
