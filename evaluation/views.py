from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from utils.mongodb import get_evaluation_collection, get_candidates_collection
from utils.decorators import login_required, admin_required
from evaluation.evaluator import is_dataset_configured, run_system_evaluation, create_demo_benchmark


@login_required
def evaluation_index(request):
    """
    Evaluation dashboard showing benchmark status, metrics, and run history.
    """
    dataset_ready = is_dataset_configured()
    eval_col = get_evaluation_collection()
    runs = list(eval_col.find({}).sort('timestamp', -1))
    
    latest_run = runs[0] if runs else None
    
    return render(request, 'evaluation/index.html', {
        'dataset_ready': dataset_ready,
        'latest_run': latest_run,
        'runs': runs,
    })


@admin_required
def run_evaluation_action(request):
    """
    Trigger a full evaluation run on the configured dataset.
    """
    if request.method == 'POST':
        try:
            run_doc = run_system_evaluation("Forensic Sketch Benchmark")
            messages.success(
                request,
                f"Evaluation completed: Top-1 Accuracy: {run_doc['top1_accuracy']}%, "
                f"Top-5: {run_doc['top5_accuracy']}%, Avg Time: {run_doc['avg_search_time']}s"
            )
        except Exception as e:
            messages.error(request, f"Evaluation error: {str(e)}")
            
    return redirect('evaluation:index')


@admin_required
def setup_benchmark_action(request):
    """
    Initialize demo benchmark dataset from candidate portraits.
    """
    if request.method == 'POST':
        try:
            count = create_demo_benchmark()
            messages.success(request, f"Initialized evaluation benchmark with {count} probe sketch test cases.")
        except Exception as e:
            messages.error(request, f"Failed to setup benchmark: {str(e)}")
            
    return redirect('evaluation:index')
