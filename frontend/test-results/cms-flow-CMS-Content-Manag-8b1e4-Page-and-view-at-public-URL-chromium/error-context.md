# Page snapshot

```yaml
- generic [active] [ref=e1]:
  - generic [ref=e2]:
    - img [ref=e4]
    - heading "Something went wrong" [level=1] [ref=e6]
    - paragraph [ref=e7]: We encountered an unexpected error. Please try refreshing the page or contact support if the issue persists.
    - button "Refresh Page" [ref=e8] [cursor=pointer]:
      - img [ref=e9]
      - text: Refresh Page
  - contentinfo [ref=e14]:
    - generic [ref=e15]:
      - generic [ref=e16]:
        - generic [ref=e17]:
          - generic [ref=e18]: ScholarFlow
          - generic [ref=e19]: Modern academic workflow platform.
        - navigation [ref=e20]:
          - link "About" [ref=e21] [cursor=pointer]:
            - /url: /journal/about
          - link "Guidelines" [ref=e22] [cursor=pointer]:
            - /url: /journal/guidelines
          - link "Contact" [ref=e23] [cursor=pointer]:
            - /url: /journal/contact
          - link "Ethics" [ref=e24] [cursor=pointer]:
            - /url: /journal/ethics
      - generic [ref=e25]: © 2026 ScholarFlow. All rights reserved.
  - region "Notifications alt+T"
  - alert [ref=e26]
  - generic [ref=e29] [cursor=pointer]:
    - img [ref=e30]
    - generic [ref=e32]: 4 errors
    - button "Hide Errors" [ref=e33]:
      - img [ref=e34]
```