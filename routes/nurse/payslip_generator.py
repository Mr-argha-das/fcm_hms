"""
payslip_generator.py
────────────────────
Nurse salary slip PDF generator using ReportLab.
Jab bhi admin salary pay kare, yeh function call hoga
aur ek professional PDF ban jayegi.
"""

import os
import uuid
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle,
    Paragraph, Spacer, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT


# ── Folder jahan PDFs save hongi ─────────────────────────────
PAYSLIP_DIR = "media/payslips"
os.makedirs(PAYSLIP_DIR, exist_ok=True)


# ─────────────────────────────────────────────────────────────
#  MAIN FUNCTION
# ─────────────────────────────────────────────────────────────

def generate_payslip_pdf(data: dict) -> str:
    """
    data dict mein ye fields chahiye:
    {
        # Hospital Info
        "hospital_name"   : "WeCare360",
        "hospital_address": "123, Main Road, Delhi",
        "hospital_phone"  : "9876543210",

        # Nurse Info
        "nurse_name"      : "Sunita Devi",
        "nurse_phone"     : "9876543210",
        "nurse_type"      : "GNM",
        "nurse_id"        : "NRS-001",

        # Salary Month
        "month"           : "2025-06",       # YYYY-MM

        # Attendance
        "total_days"      : 30,
        "present_days"    : 26,
        "absent_days"     : 4,

        # Salary Breakdown
        "basic_salary"    : 18000.0,
        "deductions"      : 500.0,
        "advance_taken"   : 1000.0,
        "net_salary"      : 16500.0,

        # Payment Info
        "amount_paid_now" : 10000.0,   # is baar diya
        "total_paid"      : 16500.0,   # abhi tak total paid
        "pending_amount"  : 0.0,
        "is_fully_paid"   : True,

        # Duty Breakdown (optional list)
        "duty_breakdown"  : [
            {
                "duty_type"   : "12HR",
                "shift"       : "DAY",
                "price_perday": 600.0,
                "days"        : 26,
                "salary"      : 15600.0,
            }
        ],
    }

    Returns: PDF file path (string)
    """

    # ── File name ──
    month_safe = data.get("month", "unknown").replace("-", "_")
    nurse_safe = (data.get("nurse_name", "nurse")).replace(" ", "_")
    filename   = f"payslip_{nurse_safe}_{month_safe}_{uuid.uuid4().hex[:6]}.pdf"
    filepath   = os.path.join(PAYSLIP_DIR, filename)

    # ── Month display ──
    try:
        y, m = data["month"].split("-")
        month_display = datetime(int(y), int(m), 1).strftime("%B %Y")   # "June 2025"
    except Exception:
        month_display = data.get("month", "")

    # ── Colors ──
    PRIMARY    = colors.HexColor("#1a3c6b")   # dark blue header
    SECONDARY  = colors.HexColor("#2e86de")   # accent blue
    LIGHT_BG   = colors.HexColor("#eaf1fb")   # light blue bg
    GREEN      = colors.HexColor("#27ae60")
    RED        = colors.HexColor("#e74c3c")
    GRAY_LINE  = colors.HexColor("#cccccc")
    WHITE      = colors.white
    BLACK      = colors.black
    TEXT_GRAY  = colors.HexColor("#555555")

    # ── Styles ──
    styles = getSampleStyleSheet()

    def style(name, **kwargs):
        return ParagraphStyle(name, **kwargs)

    s_title   = style("title",   fontSize=20, textColor=WHITE,    alignment=TA_CENTER, fontName="Helvetica-Bold")
    s_sub     = style("sub",     fontSize=10, textColor=WHITE,    alignment=TA_CENTER, fontName="Helvetica")
    s_head    = style("head",    fontSize=11, textColor=PRIMARY,  fontName="Helvetica-Bold", spaceAfter=2)
    s_normal  = style("normal2", fontSize=9,  textColor=BLACK,    fontName="Helvetica")
    s_bold    = style("bold2",   fontSize=9,  textColor=BLACK,    fontName="Helvetica-Bold")
    s_right   = style("right2",  fontSize=9,  textColor=BLACK,    fontName="Helvetica",  alignment=TA_RIGHT)
    s_green   = style("green",   fontSize=11, textColor=GREEN,    fontName="Helvetica-Bold", alignment=TA_CENTER)
    s_red     = style("red",     fontSize=10, textColor=RED,      fontName="Helvetica-Bold", alignment=TA_CENTER)
    s_center  = style("center2", fontSize=9,  textColor=TEXT_GRAY,fontName="Helvetica",  alignment=TA_CENTER)
    s_slip_no = style("slipno",  fontSize=7,  textColor=TEXT_GRAY,fontName="Helvetica",  alignment=TA_RIGHT)

    # ── Document ──
    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        rightMargin=15*mm, leftMargin=15*mm,
        topMargin=12*mm,   bottomMargin=12*mm,
    )

    W = A4[0] - 30*mm   # usable width
    story = []

    # ══════════════════════════════════════
    #  HEADER — Hospital name + title
    # ══════════════════════════════════════
    hospital_name    = data.get("hospital_name",    "WeCare360")
    hospital_address = data.get("hospital_address", "")
    hospital_phone   = data.get("hospital_phone",   "")

    header_data = [[
        Paragraph(hospital_name, s_title),
    ]]
    sub_text = f"{hospital_address}  |  Ph: {hospital_phone}" if hospital_address else ""
    if sub_text:
        header_data.append([Paragraph(sub_text, s_sub)])
    header_data.append([Paragraph(f"SALARY SLIP — {month_display.upper()}", s_sub)])

    header_table = Table(header_data, colWidths=[W])
    header_table.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, -1), PRIMARY),
        ("TOPPADDING",  (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING",(0,-1),(-1,-1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",(0, 0), (-1, -1), 10),
        ("ROUNDEDCORNERS", [6]),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 5*mm))

    # Slip number + date (top right)
    slip_no = f"Slip No: PS-{uuid.uuid4().hex[:8].upper()}   |   Generated: {datetime.utcnow().strftime('%d %b %Y, %H:%M')} UTC"
    story.append(Paragraph(slip_no, s_slip_no))
    story.append(Spacer(1, 4*mm))

    # ══════════════════════════════════════
    #  NURSE INFO + MONTH BOX
    # ══════════════════════════════════════
    nurse_name  = data.get("nurse_name",  "N/A")
    nurse_phone = data.get("nurse_phone", "N/A")
    nurse_type  = data.get("nurse_type",  "N/A")
    nurse_id    = data.get("nurse_id",    "N/A")

    info_left = [
        [Paragraph("EMPLOYEE DETAILS", s_head), ""],
        [Paragraph("Name",          s_bold), Paragraph(nurse_name,  s_normal)],
        [Paragraph("Nurse Type",    s_bold), Paragraph(nurse_type,  s_normal)],
        [Paragraph("Phone",         s_bold), Paragraph(nurse_phone, s_normal)],
        [Paragraph("Employee ID",   s_bold), Paragraph(nurse_id,    s_normal)],
    ]
    info_right = [
        [Paragraph("PAY PERIOD", s_head), ""],
        [Paragraph("Month",      s_bold), Paragraph(month_display, s_normal)],
        [Paragraph("Total Days", s_bold), Paragraph(str(data.get("total_days",   0)), s_normal)],
        [Paragraph("Present",    s_bold), Paragraph(str(data.get("present_days", 0)), s_normal)],
        [Paragraph("Absent",     s_bold), Paragraph(str(data.get("absent_days",  0)), s_normal)],
    ]

    def info_table(rows):
        t = Table(rows, colWidths=[35*mm, 50*mm])
        t.setStyle(TableStyle([
            ("BACKGROUND",   (0, 0), (-1, 0), LIGHT_BG),
            ("SPAN",         (0, 0), (-1, 0)),
            ("TOPPADDING",   (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
            ("LEFTPADDING",  (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("BOX",          (0, 0), (-1, -1), 0.5, GRAY_LINE),
            ("INNERGRID",    (0, 1), (-1, -1), 0.3, GRAY_LINE),
            ("ROUNDEDCORNERS", [4]),
        ]))
        return t

    two_col = Table(
        [[info_table(info_left), info_table(info_right)]],
        colWidths=[W/2 - 3*mm, W/2 - 3*mm],
        hAlign="LEFT"
    )
    two_col.setStyle(TableStyle([
        ("LEFTPADDING",  (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
        ("VALIGN",       (0,0), (-1,-1), "TOP"),
        ("ALIGN",        (1,0), (1,0),   "RIGHT"),
    ]))
    story.append(two_col)
    story.append(Spacer(1, 5*mm))

    # ══════════════════════════════════════
    #  DUTY BREAKDOWN TABLE
    # ══════════════════════════════════════
    duty_breakdown = data.get("duty_breakdown", [])
    if duty_breakdown:
        story.append(Paragraph("DUTY BREAKDOWN", s_head))
        story.append(Spacer(1, 2*mm))

        duty_rows = [[
            Paragraph("Duty Type", s_bold),
            Paragraph("Shift",     s_bold),
            Paragraph("Rate/Day",  s_bold),
            Paragraph("Days",      s_bold),
            Paragraph("Amount",    s_bold),
        ]]
        for d in duty_breakdown:
            duty_rows.append([
                Paragraph(d.get("duty_type", "-"),                  s_normal),
                Paragraph(d.get("shift",     "-"),                  s_normal),
                Paragraph(f"₹{d.get('price_perday', 0):,.2f}",     s_normal),
                Paragraph(str(d.get("days", 0)),                    s_normal),
                Paragraph(f"₹{d.get('salary', 0):,.2f}",           s_normal),
            ])

        duty_table = Table(
            duty_rows,
            colWidths=[35*mm, 30*mm, 35*mm, 25*mm, 40*mm],
        )
        duty_table.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0),  PRIMARY),
            ("TEXTCOLOR",     (0, 0), (-1, 0),  WHITE),
            ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, -1), 9),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING",   (0, 0), (-1, -1), 7),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 7),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, LIGHT_BG]),
            ("BOX",           (0, 0), (-1, -1), 0.5, GRAY_LINE),
            ("INNERGRID",     (0, 0), (-1, -1), 0.3, GRAY_LINE),
            ("ALIGN",         (2, 0), (-1, -1), "RIGHT"),
        ]))
        story.append(duty_table)
        story.append(Spacer(1, 5*mm))

    # ══════════════════════════════════════
    #  SALARY SUMMARY TABLE
    # ══════════════════════════════════════
    story.append(Paragraph("SALARY SUMMARY", s_head))
    story.append(Spacer(1, 2*mm))

    basic_salary  = data.get("basic_salary",  0)
    deductions    = data.get("deductions",    0)
    advance_taken = data.get("advance_taken", 0)
    net_salary    = data.get("net_salary",    0)

    def money(val):
        return f"₹{float(val):,.2f}"

    salary_rows = [
        # Header row
        [
            Paragraph("EARNINGS", s_bold),
            Paragraph("AMOUNT",   s_bold),
            Paragraph("DEDUCTIONS", s_bold),
            Paragraph("AMOUNT",     s_bold),
        ],
        [
            Paragraph("Basic Salary",   s_normal),
            Paragraph(money(basic_salary), s_normal),
            Paragraph("Absent Deduction", s_normal),
            Paragraph(money(deductions),   s_normal),
        ],
        [
            Paragraph("", s_normal),
            Paragraph("", s_normal),
            Paragraph("Advance Taken",  s_normal),
            Paragraph(money(advance_taken), s_normal),
        ],
        [
            Paragraph("GROSS TOTAL", s_bold),
            Paragraph(money(basic_salary), s_bold),
            Paragraph("TOTAL DEDUCTIONS", s_bold),
            Paragraph(money(deductions + advance_taken), s_bold),
        ],
    ]

    sal_table = Table(salary_rows, colWidths=[W*0.30, W*0.20, W*0.32, W*0.18])
    sal_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  LIGHT_BG),
        ("FONTSIZE",      (0, 0), (-1, -1), 9),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 7),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 7),
        ("BOX",           (0, 0), (-1, -1), 0.5, GRAY_LINE),
        ("INNERGRID",     (0, 0), (-1, -1), 0.3, GRAY_LINE),
        ("BACKGROUND",    (0, 3), (-1, 3),  LIGHT_BG),
        ("ALIGN",         (1, 0), (1, -1),  "RIGHT"),
        ("ALIGN",         (3, 0), (3, -1),  "RIGHT"),
    ]))
    story.append(sal_table)
    story.append(Spacer(1, 3*mm))

    # ── NET SALARY BIG BOX ──
    net_row = Table(
        [[
            Paragraph("NET SALARY (Payable)", style("ns_l", fontSize=12, fontName="Helvetica-Bold", textColor=WHITE)),
            Paragraph(money(net_salary),      style("ns_r", fontSize=13, fontName="Helvetica-Bold", textColor=WHITE, alignment=TA_RIGHT)),
        ]],
        colWidths=[W * 0.6, W * 0.4],
    )
    net_row.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), SECONDARY),
        ("TOPPADDING",    (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
        ("LEFTPADDING",   (0, 0), (-1, -1), 12),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 12),
        ("ROUNDEDCORNERS", [5]),
    ]))
    story.append(net_row)
    story.append(Spacer(1, 5*mm))

    # ══════════════════════════════════════
    #  PAYMENT STATUS TABLE
    # ══════════════════════════════════════
    story.append(Paragraph("PAYMENT DETAILS", s_head))
    story.append(Spacer(1, 2*mm))

    amount_paid_now = data.get("amount_paid_now", 0)
    total_paid      = data.get("total_paid",      0)
    pending_amount  = data.get("pending_amount",  0)
    is_fully_paid   = data.get("is_fully_paid",   False)

    payment_rows = [
        [Paragraph("Description",          s_bold),  Paragraph("Amount", s_bold)],
        [Paragraph("Paid This Transaction",s_normal), Paragraph(money(amount_paid_now), s_normal)],
        [Paragraph("Total Paid (Cumulative)", s_normal), Paragraph(money(total_paid), s_normal)],
        [Paragraph("Pending Amount",       s_bold),  Paragraph(money(pending_amount),  s_bold)],
    ]

    pay_table = Table(payment_rows, colWidths=[W * 0.65, W * 0.35])
    pay_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  LIGHT_BG),
        ("FONTSIZE",      (0, 0), (-1, -1), 9),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 7),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 7),
        ("BOX",           (0, 0), (-1, -1), 0.5, GRAY_LINE),
        ("INNERGRID",     (0, 0), (-1, -1), 0.3, GRAY_LINE),
        ("BACKGROUND",    (0, 3), (-1, 3),  colors.HexColor("#fff3cd")),
        ("ALIGN",         (1, 0), (1, -1),  "RIGHT"),
    ]))
    story.append(pay_table)
    story.append(Spacer(1, 3*mm))

    # ── PAID / PARTIAL BADGE ──
    if is_fully_paid:
        badge = Table(
            [[Paragraph("✅  SALARY FULLY PAID", s_green)]],
            colWidths=[W],
        )
        badge.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), colors.HexColor("#d4edda")),
            ("BOX",           (0,0),(-1,-1), 1, GREEN),
            ("TOPPADDING",    (0,0),(-1,-1), 8),
            ("BOTTOMPADDING", (0,0),(-1,-1), 8),
            ("ROUNDEDCORNERS", [5]),
        ]))
    else:
        badge = Table(
            [[Paragraph(f"⚠️  PARTIAL PAYMENT  —  Pending: {money(pending_amount)}", s_red)]],
            colWidths=[W],
        )
        badge.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), colors.HexColor("#fdecea")),
            ("BOX",           (0,0),(-1,-1), 1, RED),
            ("TOPPADDING",    (0,0),(-1,-1), 8),
            ("BOTTOMPADDING", (0,0),(-1,-1), 8),
            ("ROUNDEDCORNERS", [5]),
        ]))

    story.append(badge)
    story.append(Spacer(1, 8*mm))

    # ══════════════════════════════════════
    #  FOOTER
    # ══════════════════════════════════════
    story.append(HRFlowable(width=W, thickness=0.5, color=GRAY_LINE))
    story.append(Spacer(1, 3*mm))

    footer_rows = [[
        Paragraph(
            "This is a system-generated salary slip and does not require a physical signature.",
            style("footer", fontSize=7, textColor=TEXT_GRAY, alignment=TA_CENTER)
        )
    ]]
    footer_table = Table(footer_rows, colWidths=[W])
    story.append(footer_table)

    # ── Build PDF ──
    doc.build(story)
    return filepath