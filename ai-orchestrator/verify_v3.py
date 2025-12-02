"""Verify v3 architecture functionality.

This script checks if v3 components can be imported and initialized.
"""

import sys


def verify_imports():
    """Verify all v3 components can be imported."""
    print("🔍 Verifying v3 imports...")
    
    try:
        from app.core.graph_v3 import build_agent_graph_v3, get_agent_graph_v3
        print("✅ graph_v3 imports OK")
    except Exception as e:
        print(f"❌ graph_v3 import failed: {e}")
        return False
    
    try:
        from app.core.orchestrator import Orchestrator, get_orchestrator
        print("✅ orchestrator imports OK")
    except Exception as e:
        print(f"❌ orchestrator import failed: {e}")
        return False
    
    try:
        from app.api.chat_v3 import router
        print("✅ chat_v3 API imports OK")
    except Exception as e:
        print(f"❌ chat_v3 API import failed: {e}")
        return False
    
    try:
        from app.agents.setup import register_all_agents
        from app.agents.registry import get_agent_registry
        print("✅ agents imports OK")
    except Exception as e:
        print(f"❌ agents import failed: {e}")
        return False
    
    return True


def verify_agents():
    """Verify agents can be registered."""
    print("\n🔍 Verifying agent registration...")
    
    try:
        from app.agents.setup import register_all_agents
        from app.agents.registry import get_agent_registry
        
        register_all_agents()
        registry = get_agent_registry()
        agents = registry.list_agents()
        
        print(f"✅ Registered {len(agents)} agents:")
        for agent in agents:
            print(f"   - {agent.name}: {agent.description[:50]}...")
        
        return True
    except Exception as e:
        print(f"❌ Agent registration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_graph():
    """Verify v3 graph can be built."""
    print("\n🔍 Verifying v3 graph...")
    
    try:
        from app.core.graph_v3 import build_agent_graph_v3
        
        graph = build_agent_graph_v3()
        print("✅ v3 graph built successfully")
        print(f"   Nodes: {list(graph.nodes.keys())}")
        
        return True
    except Exception as e:
        print(f"❌ v3 graph build failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all verifications."""
    print("=" * 60)
    print("AI Orchestrator v3 Architecture Verification")
    print("=" * 60)
    
    results = []
    
    # Test imports
    results.append(("Imports", verify_imports()))
    
    # Test agent registration
    results.append(("Agent Registration", verify_agents()))
    
    # Test graph building
    results.append(("Graph Building", verify_graph()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary:")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {name}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("\n🎉 All v3 components verified successfully!")
        print("v3 architecture is ready to replace v2.")
        return 0
    else:
        print("\n⚠️  Some v3 components failed verification.")
        print("Please fix the issues before proceeding with migration.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

