"""
Test script to verify ReportLab installation and TableStyle import
"""

import sys
print(f"Python version: {sys.version}")

print("Attempting to import ReportLab modules...")

try:
    import reportlab
    print(f"ReportLab version: {reportlab.__version__}")
    
    # Try to import TableStyle from different locations
    try:
        from reportlab.platypus.tables import TableStyle
        print("✓ Successfully imported TableStyle from reportlab.platypus.tables")
    except ImportError:
        print("✗ Failed to import TableStyle from reportlab.platypus.tables")
    
    try:
        from reportlab.lib.tables import TableStyle
        print("✓ Successfully imported TableStyle from reportlab.lib.tables")
    except ImportError:
        print("✗ Failed to import TableStyle from reportlab.lib.tables")
    
    # Try to import and use Table
    try:
        from reportlab.platypus import Table
        data = [["A1", "B1"], ["A2", "B2"]]
        table = Table(data)
        print("✓ Successfully created a Table object")
        
        # Try to use TableStyle with the table
        try:
            from reportlab.platypus.tables import TableStyle
            style = TableStyle([('GRID', (0, 0), (-1, -1), 1, 'black')])
            table.setStyle(style)
            print("✓ Successfully applied TableStyle to Table")
        except Exception as e:
            print(f"✗ Failed to apply TableStyle to Table: {e}")
            
    except Exception as e:
        print(f"✗ Failed to create a Table object: {e}")
    
except ImportError as e:
    print(f"✗ Failed to import ReportLab: {e}")

print("Test completed.") 