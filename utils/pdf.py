from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle,
    Paragraph, Spacer, PageBreak
)
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from io import BytesIO
from datetime import datetime
from collections import defaultdict


# =========================
# 日本語フォント
# =========================
pdfmetrics.registerFont(UnicodeCIDFont("HeiseiKakuGo-W5"))


# =========================
# 訓練一覧PDF生成
# =========================
def create_training_pdf(trainings, fiscal_year):

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=30,
        rightMargin=30,
        topMargin=30,
        bottomMargin=30
    )

    styles = getSampleStyleSheet()

    # =========================
    # カスタムスタイル
    # =========================
    title_style = ParagraphStyle(
        "TitleJP",
        parent=styles["Title"],
        fontName="HeiseiKakuGo-W5",
        fontSize=18,
        alignment=1,  # 中央
        spaceAfter=10
    )

    sub_style = ParagraphStyle(
        "SubJP",
        parent=styles["Normal"],
        fontName="HeiseiKakuGo-W5",
        fontSize=10,
        alignment=1,
        spaceAfter=20
    )

    header_style = ParagraphStyle(
        "HeaderJP",
        parent=styles["Normal"],
        fontName="HeiseiKakuGo-W5",
        fontSize=12,
        spaceBefore=10,
        spaceAfter=6
    )

    normal_style = ParagraphStyle(
        "NormalJP",
        parent=styles["Normal"],
        fontName="HeiseiKakuGo-W5",
        fontSize=10
    )

    elements = []

    # =========================
    # タイトル
    # =========================
    elements.append(Paragraph(f"{fiscal_year}年度 長島方面団第３分団訓練計画", title_style))
    elements.append(Paragraph("（年間予定一覧）", sub_style))

    # =========================
    # 日付
    # =========================
    created_at = datetime.now().strftime("%Y年%m月%d日 %H:%M作成")
    elements.append(Paragraph(f"作成日時：{created_at}", normal_style))
    elements.append(Spacer(1, 10))

    # =========================
    # 月ごとに整理
    # =========================
    grouped = defaultdict(list)

    for t in trainings:
        d = datetime.strptime(t["date"], "%Y-%m-%d")
        month = d.month
        grouped[month].append(t)

    # 月順に並べる
    for month in sorted(grouped.keys()):

        # =========================
        # 月タイトル
        # =========================
        elements.append(Paragraph(f"■ {month}月", header_style))

        # =========================
        # テーブルデータ
        # =========================
        data = [
            ["日付", "訓練内容", "場所", "時間", "対象", "備考"]
        ]

        # ★ 月ごとにソート
        sorted_trainings = sorted(
            grouped[month],
            key=lambda x: x["date"]
        )

        for t in sorted_trainings:

            d = datetime.strptime(t["date"], "%Y-%m-%d")
            date_str = d.strftime("%m/%d")

            title = t["title"]
            location = t["location"] or "-"
            time = f"{t['start_time'] or ''}〜{t['end_time'] or ''}"
            note = t["note"] or ""

            target = t.get("target_label", "全員")

            data.append([
                date_str,
                Paragraph(title, normal_style),
                location,
                time,
                target,
                note
            ])

        # =========================
        # 列幅（超重要）
        # =========================
        col_widths = [50, 130, 90, 70, 80, 90]

        table = Table(data, colWidths=col_widths, repeatRows=1)

        table.setStyle(TableStyle([
            # ヘッダー
            ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),

            # フォント
            ("FONTNAME", (0, 0), (-1, -1), "HeiseiKakuGo-W5"),

            # サイズ
            ("FONTSIZE", (0, 0), (-1, -1), 9),

            # 中央揃え（内容以外）
            ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ("ALIGN", (2, 0), (-1, -1), "CENTER"),

            # 内容は左寄せ
            ("ALIGN", (1, 1), (1, -1), "LEFT"),

            # グリッド
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),

            # 余白
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))

        elements.append(table)
        elements.append(Spacer(1, 10))

    # =========================
    # フッター的な説明
    # =========================
    elements.append(Spacer(1, 20))
    elements.append(Paragraph(
        "※本計画は予定であり、天候・災害等により変更となる場合があります。",
        normal_style
    ))

    # =========================
    # PDF生成
    # =========================
    doc.build(elements)

    buffer.seek(0)

    return buffer


# =========================
# 自治会別団員配置PDF
# =========================
def boxed_paragraph(text, style, bg_color=None, border_color=colors.black):
    table = Table([[Paragraph(text, style)]], colWidths=[480])

    table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 1, border_color),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))

    if bg_color:
        table.setStyle([("BACKGROUND", (0, 0), (-1, -1), bg_color)])

    return table

def create_unit_summary_pdf(units, target_date):

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=30,
        rightMargin=30,
        topMargin=30,
        bottomMargin=30
    )

    styles = getSampleStyleSheet()

    # =========================
    # スタイル
    # =========================
    title_style = ParagraphStyle(
        "TitleJP",
        parent=styles["Title"],
        fontName="HeiseiKakuGo-W5",
        fontSize=16,
        alignment=1,
        spaceAfter=10
    )

    sub_style = ParagraphStyle(
        "SubJP",
        parent=styles["Normal"],
        fontName="HeiseiKakuGo-W5",
        fontSize=10,
        alignment=1,
        spaceAfter=15
    )

    header_style = ParagraphStyle(
        "HeaderJP",
        parent=styles["Normal"],
        fontName="HeiseiKakuGo-W5",
        fontSize=12,
        spaceBefore=10,
        spaceAfter=4
    )

    normal_style = ParagraphStyle(
        "NormalJP",
        parent=styles["Normal"],
        fontName="HeiseiKakuGo-W5",
        fontSize=10
    )

    elements = []

    # =========================
    # タイトル
    # =========================
    elements.append(
        boxed_paragraph(
            "自治会別団員配置状況",
            title_style,
            bg_color=colors.lightgrey
        )
    )

    elements.append(Paragraph(
        f"（{target_date} 時点）",
        sub_style
    ))

    # =========================
    # 作成日時
    # =========================
    created_at = datetime.now().strftime("%Y年%m月%d日 %H:%M作成")
    elements.append(Paragraph(f"作成日時：{created_at}", normal_style))
    elements.append(Spacer(1, 10))

    # =========================
    # 全体集計
    # =========================
    total_required = sum(u["required_members"] or 0 for u in units)
    total_current = sum(u["member_count"] or 0 for u in units)
    total_diff = total_current - total_required

    elements.append(Paragraph("■ 全体状況", header_style))

    elements.append(Spacer(1, 10))

    elements.append(
        boxed_paragraph(
            f"団員数：{total_current}人 ｜ 定数：{total_required}人 ｜ 過不足：{total_diff:+}",
            normal_style,
            bg_color=colors.whitesmoke
        )
    )

    elements.append(Spacer(1, 10))

    elements.append(Paragraph("■ 自治会別状況", header_style))

    elements.append(Spacer(1, 10))


    # =========================
    # 不足順にソート（重要）
    # =========================
    units_sorted = sorted(
        units,
        key=lambda x: (x["member_count"] - x["required_members"])
    )

    shortage_list = []

    # =========================
    # 自治会ごと表示
    # =========================
    for u in units_sorted:

        name = u["name"]
        current = u["member_count"] or 0
        required = u["required_members"] or 0
        diff = current - required

        members = u["member_names"] or "なし"

        color = "red" if diff < 0 else "black"

        if diff < 0:
            shortage_list.append(f"{name}（{diff}人不足）")

        text = f"""
        <b>{name}</b><br/>
        <font color='{color}'>
        人数：{current} ｜ 定数：{required} ｜ 過不足：{diff:+}
        </font><br/>
        団員一覧：<br/>{members}
        """

        elements.append(
            boxed_paragraph(text, normal_style)
        )

        elements.append(Spacer(1, 6))

    # =========================
    # 不足自治会まとめ（超重要）
    # =========================
    if shortage_list:
        elements.append(Spacer(1, 10))
        elements.append(Paragraph("■ 要補充自治会", header_style))

        for s in shortage_list:
            elements.append(Paragraph(s, normal_style))

    # =========================
    # フッター
    # =========================
    elements.append(Spacer(1, 20))
    elements.append(Paragraph(
        "※本資料は指定時点の団員情報を基に作成しています。",
        normal_style
    ))

    # =========================
    # PDF生成
    # =========================
    doc.build(elements)

    buffer.seek(0)

    return buffer