import models
import parse_pdf
import pymupdf

year, _ = parse_pdf.read_cimb(pymupdf.open("D:/Personal_Documents/Finances/mutasi/cimb/payroll/casa_statement_31-01-2025_459088755.pdf"), "190100")

print(year)