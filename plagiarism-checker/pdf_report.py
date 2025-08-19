from weasyprint import HTML

def render_results_pdf(html_fragment: str) -> bytes:
    html = f"""
    <html><head>
    <meta charset='utf-8'>
    <style>
      body {{ font-family: Arial, sans-serif; margin: 24px; }}
      h1,h2,h3 {{ margin: 0.2em 0; }}
      .score {{ font-size: 20px; font-weight: bold; }}
      .card {{ border: 1px solid #ddd; border-radius: 12px; padding: 14px; margin: 12px 0; }}
      a {{ word-break: break-all; }}
      .muted {{ color: #666; }}
    </style>
    </head><body>
    {html_fragment}
    </body></html>
    """
    return HTML(string=html).write_pdf()
