try:
    from weasyprint import HTML
    print("WEASYPRINT_OK")
except Exception as e:
    import traceback
    print(f"WEASYPRINT_ERROR: {str(e)}")
    print(traceback.format_exc())
