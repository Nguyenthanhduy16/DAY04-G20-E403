---
name: hn_search
track: team_new
kind: live_api
provider: Hacker News (Algolia public index)
requires_env: []
inputs: [query, sort_by, limit, min_points]
outputs: [items, item_count]
side_effect: false
---
# hn_search

Tìm story trên Hacker News qua public Algolia index
(`https://hn.algolia.com/api/v1/search`). Không cần API key, không tính quota.

## Vì sao team viết tool này

Ba tool có sẵn phủ ba nguồn khác nhau nhưng còn thiếu một nguồn mà research agent
về AI/tech hay cần: thảo luận của cộng đồng developer.

| Nguồn | Tool | Trả về |
|---|---|---|
| Web mở / báo chí | `lookup` | bài viết đã xuất bản |
| Twitter/X | `social_search` | post cá nhân |
| Hacker News | `hn_search` | story kèm điểm và số comment của dev community |

`hn_search` khác `social_search` ở chỗ nó có tín hiệu chọn lọc thật (`points`,
`num_comments`), nên trả lời được câu "cái này có được đón nhận không" chứ không
chỉ "có ai nhắc tới không".

## Arguments

| Arg | Kiểu | Mặc định | Ghi chú |
|---|---|---|---|
| `query` | string | — | Bắt buộc, không rỗng. Chỉ chứa chủ đề. |
| `sort_by` | `relevance` \| `recent` | `relevance` | `recent` đổi sang endpoint `search_by_date`. |
| `limit` | int | 5 | Kẹp trong khoảng 1–20. |
| `min_points` | int | 0 | >0 thì thêm `numericFilters=points>=N`, dùng khi user hỏi bài "nổi bật/được upvote nhiều". |

## Output

```json
{
  "tool": "hn_search",
  "query": "...", "sort_by": "...", "min_points": 0, "item_count": 5,
  "items": [
    {
      "title": "...", "url": "...", "source": "...",
      "summary": "312 points, 145 comments on Hacker News",
      "points": 312, "num_comments": 145,
      "author": "...", "created_at": "...",
      "discussion_url": "https://news.ycombinator.com/item?id=..."
    }
  ]
}
```

`items[*]` giữ đúng bốn field `title/url/source/summary` mà `format` cần, nên có
thể nối thẳng `hn_search` → `format` không cần bước chuyển đổi.

`url` là link bài gốc; nếu story là text post của HN thì `url` fallback về chính
`discussion_url`.

## Lỗi

Trả `{"tool": "hn_search", "error": ..., "message": ...}` khi `query` rỗng,
`sort_by` ngoài enum, hoặc HTTP lỗi. Không raise ra ngoài.

## Quicktest

```bash
python -c "from pathlib import Path; from env_loader import load_lab_env; load_lab_env(Path.cwd()); from tools import TOOL_FUNCTIONS as T; r=T['hn_search']('AI agents', limit=2); items=r.get('items') or []; print({'error':r.get('error'), 'item_count':len(items), 'first_title':items[0].get('title') if items else None})"
```

PASS khi `error` là `None` và `items` không rỗng.
