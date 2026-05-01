from fpdf import FPDF

# Simple version without custom font handling
pdf = FPDF()
pdf.add_page()
pdf.set_font("helvetica", "B", 16)
pdf.cell(40, 10, "Project Abstract: CDASB")
pdf.ln(10)
pdf.set_font("helvetica", "", 12)
pdf.multi_cell(0, 10, "This is a simplified abstract for the Conflict-Driven Autonomous System Builder (CDASB).")
pdf.output("abstract_simple.pdf")
print("PDF created successfully: abstract_simple.pdf")
