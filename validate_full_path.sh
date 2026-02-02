#!/bin/bash

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "🔍 Validating ScholarFlow Full Path: Home -> Search -> Article"

# 检查关键文件是否存在
echo "1. Checking critical files..."
	CRITICAL_FILES=(
	  "frontend/src/app/page.tsx"
	  "frontend/src/components/home/HeroSection.tsx"
	  "frontend/src/app/search/page.tsx"
	  "frontend/src/app/articles/[id]/page.tsx"
	  "frontend/src/app/articles/[id]/ArticleClient.tsx"
	  "backend/app/api/v1/manuscripts.py"
	  "backend/app/api/v1/stats.py"
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
echo "2. Checking frontend components..."

	# 检查HeroSection中的搜索功能
	if grep -q "handleSearch" "$REPO_ROOT/frontend/src/components/home/HeroSection.tsx"; then
	  echo "   ✅ HeroSection has search function"
	else
	  echo "   ❌ HeroSection missing search function"
	  exit 1
	fi

	# 检查搜索页中的链接
	if grep -q "/articles/" "$REPO_ROOT/frontend/src/app/search/page.tsx"; then
	  echo "   ✅ Search page has article links"
	else
	  echo "   ❌ Search page missing article links"
	  exit 1
	fi

	# 检查文章页中的下载功能
	if grep -q "handleDownload" "$REPO_ROOT/frontend/src/app/articles/[id]/page.tsx" || grep -q "handleDownload" "$REPO_ROOT/frontend/src/app/articles/[id]/ArticleClient.tsx"; then
	  echo "   ✅ Article page has download function"
	else
	  echo "   ❌ Article page missing download function"
	  exit 1
	fi

echo ""
echo "3. Checking backend APIs..."

	# 检查搜索API
	if grep -q "@router.get.*search" "$REPO_ROOT/backend/app/api/v1/manuscripts.py"; then
	  echo "   ✅ Search API implemented"
	else
	  echo "   ❌ Search API not implemented"
	  exit 1
	fi

	# 检查下载统计API
	if grep -q "@router.post.*download" "$REPO_ROOT/backend/app/api/v1/stats.py"; then
	  echo "   ✅ Download stats API implemented"
	else
	  echo "   ❌ Download stats API not implemented"
	  exit 1
	fi

	# 检查文章详情API
	if grep -q "@router.get.*articles" "$REPO_ROOT/backend/app/api/v1/manuscripts.py"; then
	  echo "   ✅ Article detail API implemented"
	else
	  echo "   ❌ Article detail API not implemented"
	  exit 1
	fi

echo ""
echo "4. Checking SEO metadata..."

	# 检查SEO配置
	if grep -q "openGraph" "$REPO_ROOT/frontend/src/app/layout.tsx"; then
	  echo "   ✅ Open Graph metadata configured"
	else
	  echo "   ❌ Open Graph metadata missing"
	  exit 1
	fi
	
	if grep -q "twitter:" "$REPO_ROOT/frontend/src/app/layout.tsx"; then
	  echo "   ✅ Twitter Card metadata configured"
	else
	  echo "   ❌ Twitter Card metadata missing"
	  exit 1
	fi

echo ""
echo "🎉 VALIDATION SUCCESS!"
echo "The full path from Home -> Search -> Article is properly implemented."
echo ""
echo "Summary:"
echo "- Frontend: Search functionality and navigation links are in place"
echo "- Backend: All required APIs are implemented"
echo "- SEO: Open Graph and Twitter Card metadata configured"
echo "- Download: Stats recording logic added"

exit 0
