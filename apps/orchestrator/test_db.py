"""
Test script to verify database connections work properly.
"""
import asyncio
from db import init_db
from repositories import FlowRepository, WorkflowRunRepository

async def test_db():
    """Test database connections and repository operations."""
    print("Initializing database...")
    await init_db()
    
    # Test flow repository
    print("Testing FlowRepository...")
    test_flow = {
        'name': 'Test Flow',
        'nodes': [
            {
                'id': 'node1',
                'type': 'writer',
                'position': {'x': 100, 'y': 100},
                'data': {'prompt': 'Test prompt'}
            }
        ],
        'edges': []
    }
    
    flow_result = await FlowRepository.save(test_flow)
    print(f"Flow saved successfully with ID: {flow_result['id']}")
    
    # Test workflow run repository
    print("Testing WorkflowRunRepository...")
    test_run = {
        'run_id': 'test-run-1',
        'flow_id': flow_result['id'],
        'status': 'running',
        'progress': 0,
        'total_steps': 1
    }
    
    run_result = await WorkflowRunRepository.save(test_run)
    print(f"Workflow run saved successfully with ID: {run_result['id']}")
    
    # Test retrieving data
    flow = await FlowRepository.get_by_id(flow_result['id'])
    print(f"Retrieved flow: {flow['name']}")
    
    run = await WorkflowRunRepository.get_by_run_id(run_result['id'])
    print(f"Retrieved run status: {run['status']}")
    
    print("All tests passed successfully!")

if __name__ == "__main__":
    asyncio.run(test_db())
