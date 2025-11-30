"""
Optimization components for Campaign Automation.

This package contains budget optimizers, A/B test managers,
and rule engines for automated campaign optimization.
"""

from app.modules.campaign_automation.optimizers.budget_optimizer import BudgetOptimizer

# TODO: Import remaining optimizers when implemented in tasks 7, 8
# from .ab_test_manager import ABTestManager
# from .rule_engine import RuleEngine

__all__ = ["BudgetOptimizer"]
