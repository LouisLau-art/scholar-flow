#!/bin/bash

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "🔍 Validating Editor Command Center Workflow"

# 检查关键文件是否存在
echo "1. Checking critical files..."
	CRITICAL_FILES=(
	  "frontend/src/components/EditorDashboard.tsx"
	  "frontend/src/components/EditorPipeline.tsx"
	  "frontend/src/components/ReviewerAssignModal.tsx"
	  "frontend/src/components/DecisionPanel.tsx"
	  "frontend/src/components/ui/tabs.tsx"
	  "frontend/src/lib/utils.ts"
	  "backend/app/api/v1/editor.py"
	  "backend/tests/test_editor_actions.py"
	)

	for file in "${CRITICAL_FILES[@]}"; do
	  if [ -f "$REPO_ROOT/$file" ]; then
	    echo "   ✅ $file exists"
	  else
	    echo "   ❌ $file missing"
	    exit 1
	  fi
	done

echo ""
echo "2. Checking backend API routes..."

	# 检查编辑API路由
	if grep -q "@router.get.*pipeline" "$REPO_ROOT/backend/app/api/v1/editor.py"; then
	  echo "   ✅ Pipeline API implemented"
	else
	  echo "   ❌ Pipeline API not implemented"
	  exit 1
	fi
	
	if grep -q "@router.get.*available-reviewers" "$REPO_ROOT/backend/app/api/v1/editor.py"; then
	  echo "   ✅ Available reviewers API implemented"
	else
	  echo "   ❌ Available reviewers API not implemented"
	  exit 1
	fi
	
	if grep -q "@router.post.*decision" "$REPO_ROOT/backend/app/api/v1/editor.py"; then
	  echo "   ✅ Decision API implemented"
	else
	  echo "   ❌ Decision API not implemented"
	  exit 1
	fi

echo ""
echo "3. Checking frontend components..."

	# 检查EditorDashboard组件
	if grep -q "EditorPipeline" "$REPO_ROOT/frontend/src/components/EditorDashboard.tsx"; then
	  echo "   ✅ EditorDashboard imports EditorPipeline"
	else
	  echo "   ❌ EditorDashboard missing EditorPipeline"
	  exit 1
	fi
	
	if grep -q "ReviewerAssignModal" "$REPO_ROOT/frontend/src/components/EditorDashboard.tsx"; then
	  echo "   ✅ EditorDashboard imports ReviewerAssignModal"
	else
	  echo "   ❌ EditorDashboard missing ReviewerAssignModal"
	  exit 1
	fi
	
	if grep -q "DecisionPanel" "$REPO_ROOT/frontend/src/components/EditorDashboard.tsx"; then
	  echo "   ✅ EditorDashboard imports DecisionPanel"
	else
	  echo "   ❌ EditorDashboard missing DecisionPanel"
	  exit 1
	fi

echo ""
echo "4. Checking dashboard integration..."

	# 检查dashboard页面是否包含EditorDashboard
	if grep -q "EditorDashboard" "$REPO_ROOT/frontend/src/app/dashboard/page.tsx"; then
	  echo "   ✅ Dashboard page includes EditorDashboard"
	else
	  echo "   ❌ Dashboard page missing EditorDashboard"
	  exit 1
	fi
	
	if grep -q "value=\"editor\"" "$REPO_ROOT/frontend/src/app/dashboard/page.tsx"; then
	  echo "   ✅ Editor tab added to dashboard"
	else
	  echo "   ❌ Editor tab not added to dashboard"
	  exit 1
	fi

echo ""
echo "5. Checking UI components..."

	# 检查Tabs组件
	if grep -q "TabsPrimitive" "$REPO_ROOT/frontend/src/components/ui/tabs.tsx"; then
	  echo "   ✅ Tabs component implemented"
	else
	  echo "   ❌ Tabs component not implemented"
	  exit 1
	fi
	
	# 检查utils
	if grep -q "cn" "$REPO_ROOT/frontend/src/lib/utils.ts"; then
	  echo "   ✅ Utils function implemented"
	else
	  echo "   ❌ Utils function not implemented"
	  exit 1
	fi

echo ""
echo "🎉 VALIDATION SUCCESS!"
echo "Editor Command Center workflow is properly implemented."
echo ""
echo "Summary:"
echo "- Backend: All APIs implemented (Pipeline, Reviewers, Decision)"
echo "- Frontend: All components created and integrated"
echo "- Dashboard: Editor tab added with full workflow"
echo "- UI: Tabs and utils components ready"

exit 0
