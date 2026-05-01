from fpdf import FPDF

class SimplePDF(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 16)
        self.cell(0, 10, 'Project Abstract', ln=1, align='C')
        self.ln(10)

def generate():
    pdf = SimplePDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    
    with open("abstract.md", "r") as f:
        lines = f.readlines()
        
    for line in lines:
        line = line.strip().replace('**', '')
        if not line:
            pdf.ln(5)
            continue
        
        if line.startswith('# '):
            pdf.set_font("Helvetica", 'B', 18)
            pdf.multi_cell(0, 10, line[2:])
        elif line.startswith('## '):
            pdf.set_font("Helvetica", 'B', 14)
            pdf.multi_cell(0, 10, line[3:])
        else:
            pdf.set_font("Helvetica", size=12)
            pdf.multi_cell(0, 10, line)
            
    pdf.output("abstract.pdf")
    print("Generated abstract.pdf")

if __name__ == "__main__":
    generate()
