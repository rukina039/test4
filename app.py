# app.py
import os
import uuid
import json
from flask import Flask, request, render_template, redirect, url_for, session, flash, jsonify
from datetime import datetime
from collections import defaultdict
from functools import wraps
from filelock import FileLock

from models import Expense

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "YOUR_SECURE_SECRET_KEY")  # 本番では安全なキーに変更

# JSONファイルの設定
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data.json')
LOCK_FILE = DATA_FILE + '.lock'

PASSWORD = os.environ.get("APP_PASSWORD", "eringi39")  # 本番では安全なパスワードに変更

# タグ自動分類用マッピング
TAG_MAPPING = [
    ("amazon", "Amazon"),
    ("ピアゴ", "食費"),
    ("マクドナルド", "娯楽費(外食費等)"),
    ("ヤオスズ", "食費"),
    ("ダイソー", "生活費(日用品等)"),
    ("セリア", "生活費(日用品等)"),
    ("サイゼリア", "娯楽費(外食費等)"),
    ("ニトリ", "生活費(日用品等)"),
    ("udemy", "自己投資"),
    ("餃子", "娯楽費(外食費等)"),
    ("ＥＸ", "交通費"),
    ("アウトレット", "生活費(日用品等)"),
    ("バス", "交通費"),
    ("セブン", "娯楽費(外食費等)"),
    ("ミニストップ", "娯楽費(外食費等)"),
    ("ソフトバンク", "生活費(日用品等)"),
    ("乙女屋", "交際費"),
    ("もみの木", "娯楽費(外食費等)"),
    ("赤から", "娯楽費(外食費等)"),
    ("openai", "自己投資"),
    ("coco壱", "娯楽費(外食費等)"),
    ("スシロー", "娯楽費(外食費等)"),
    ("gifta", "立替"),
    ("電力", "生活費(日用品等)"),
    ("オイル", "生活費(日用品等)"),
    ("大東", "生活費(日用品等)"),
    ("パン", "娯楽費(外食費等)"),
    ("スギ", "生活費(日用品等)"),
    ("丸亀製麺", "娯楽費(外食費等)"),
    ("Ｓｕｉｃａ", "交通費"),
    ("コーラ", "娯楽費(外食費等)"),
    ("カレー", "娯楽費(外食費等)"),
    ("エディオン", "生活費(日用品等)"),
    ("ベルマート", "生活費(日用品等)"),
    ("Ｈａｉｒ", "自己投資"),
    ("フアミリ", "娯楽費(外食費等)"),
    ("Ｃａｎａｌ", "娯楽費(外食費等)"),
    ("くら寿司", "娯楽費(外食費等)"),
    ("ワッツ", "生活費(日用品等)"),
    ("ＤＣＭ", "生活費(日用品等)"),
    ("ローソン", "生活費(日用品等)"),
    ("ＥＮＥＯＳ", "生活費(日用品等)"),
    ("コメダ", "娯楽費(外食費等)"),
    ("すき家", "娯楽費(外食費等)")
]

def parse_amount(amount_str):
    """例: '1,500円' や '100.99円' を整数（円単位）に変換（小数点以下は切り捨て）"""
    cleaned = amount_str.replace("円", "").replace(",", "").strip()
    try:
        return int(float(cleaned))
    except ValueError:
        return 0

def automatic_tagging(store_name):
    """店舗名から自動的にタグを返す（マッピングに一致しなければ 'その他'）"""
    lower = store_name.lower()
    for kw, tg in TAG_MAPPING:
        if kw.lower() in lower:
            return tg
    return "その他"

def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            flash("ログインが必要です。", "error")
            return redirect(url_for("login"))
        return func(*args, **kwargs)
    return wrapper

def load_data():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=4)
    with FileLock(LOCK_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)

def save_data(data):
    with FileLock(LOCK_FILE):
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        pw = request.form.get("password")
        if pw == PASSWORD:
            session["logged_in"] = True
            flash("ログインしました。", "success")
            return redirect(url_for("index"))
        else:
            flash("パスワードが違います。", "error")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    flash("ログアウトしました。", "success")
    return redirect(url_for("login"))

@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    try:
        if request.method == "POST":
            submit_type = request.form.get("submit_type", "")
            data = load_data()
            if submit_type == "add_manual":
                date_str = request.form.get("date", "")
                store_str = request.form.get("store", "")
                amount_str = request.form.get("amount", "")
                tag_str = request.form.get("tag", "")
                det_str = request.form.get("details", "")
                if date_str and store_str and amount_str:
                    amt = parse_amount(amount_str)
                    auto_tag = automatic_tagging(store_str) if not tag_str else tag_str.strip()
                    new_expense = Expense(
                        id=str(uuid.uuid4()),
                        date=date_str.strip(),
                        store=store_str.strip(),
                        amount=amt,
                        tag=auto_tag,
                        details=det_str.strip()
                    )
                    data.append(new_expense.to_dict())
                    save_data(data)
                    flash("新規出費を追加しました。", "success")
            elif submit_type == "add_paste":
                paste_data = request.form.get("paste_data", "")
                if paste_data:
                    lines = [ln.strip() for ln in paste_data.split("\n") if ln.strip()]
                    idx = 0
                    added_count = 0
                    while idx + 4 < len(lines):
                        try:
                            y_line = lines[idx].rstrip("/")
                            md_line = lines[idx+1].rstrip("/")
                            store_line = lines[idx+2]
                            amt_line = lines[idx+4]
                            try:
                                yy = int(y_line)
                                mm, dd = map(int, md_line.split("/"))
                                dt = datetime(yy, mm, dd)
                                date_str = dt.strftime("%Y-%m-%d")
                            except:
                                idx += 5
                                continue
                            amt_val = parse_amount(amt_line)
                            auto_tag = automatic_tagging(store_line)
                            new_expense = Expense(
                                id=str(uuid.uuid4()),
                                date=date_str,
                                store=store_line,
                                amount=amt_val,
                                tag=auto_tag,
                                details=""
                            )
                            data.append(new_expense.to_dict())
                            added_count += 1
                            idx += 5
                        except IndexError:
                            break
                    save_data(data)
                    flash(f"ペースト入力の出費を追加しました。({added_count}件)", "success")
            elif submit_type == "delete_selected":
                selected_ids = request.form.getlist("selected_ids")
                if selected_ids:
                    data = [item for item in data if item['id'] not in selected_ids]
                    save_data(data)
                    flash(f"{len(selected_ids)}件のデータを削除しました。", "success")
                else:
                    flash("削除対象が選択されていません。", "error")
            elif submit_type == "delete_all":
                save_data([])
                flash("すべてのデータを削除しました。", "success")
        # ---------------------
        # データ読み込み＆フィルタリング
        # ---------------------
        data = load_data()
        filtered_data = [Expense(**item) for item in data]

        yymm = request.args.get("year_month", "")
        if yymm:
            filtered_data = [exp for exp in filtered_data if exp.date.startswith(f"{yymm}-")]

        start_date_str = request.args.get("start_date", "").strip()
        end_date_str = request.args.get("end_date", "").strip()
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                filtered_data = [exp for exp in filtered_data if datetime.strptime(exp.date, "%Y-%m-%d").date() >= start_date]
            except ValueError:
                pass
        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
                filtered_data = [exp for exp in filtered_data if datetime.strptime(exp.date, "%Y-%m-%d").date() <= end_date]
            except ValueError:
                pass

        f_tag = request.args.get("filter_tag", "").strip()
        if f_tag:
            filtered_data = [exp for exp in filtered_data if exp.tag == f_tag]

        sort_order = request.args.get("sort_order", "asc").strip().lower()
        if sort_order not in ["asc", "desc"]:
            sort_order = "asc"
        filtered_data = sorted(filtered_data, key=lambda x: x.date, reverse=(sort_order=="desc"))

        overall_line = defaultdict(int)
        for exp in filtered_data:
            ym = exp.date[:7]
            overall_line[ym] += exp.amount

        unique_months = sorted({exp.date[:7] for exp in [Expense(**item) for item in data]})
        all_months_sorted = sorted({exp.date[:7] for exp in filtered_data})
        overall_dataset = [overall_line[m] for m in all_months_sorted]

        cat_data = defaultdict(lambda: defaultdict(int))
        for exp in filtered_data:
            tg = exp.tag or "その他"
            ym = exp.date[:7]
            cat_data[tg][ym] += exp.amount
        tags_sorted = sorted(cat_data.keys())
        cat_charts = {}
        for cat in tags_sorted:
            cat_charts[cat] = [cat_data[cat].get(m, 0) for m in all_months_sorted]

        latest_month = all_months_sorted[-1] if all_months_sorted else ""

        stacked_datasets = []
        color_palette = [
            'rgba(54,162,235,0.7)', 'rgba(255,206,86,0.7)',
            'rgba(75,192,192,0.7)', 'rgba(153,102,255,0.7)',
            'rgba(255,159,64,0.7)', 'rgba(255,99,132,0.7)',
            'rgba(201,203,207,0.7)', 'rgba(0,255,0,0.7)',
            'rgba(0,0,255,0.7)', 'rgba(255,255,0,0.7)'
        ]
        for i, cat in enumerate(tags_sorted):
            stacked_datasets.append({
                "label": cat,
                "data": cat_charts[cat],
                "borderColor": color_palette[i % len(color_palette)],
                "backgroundColor": color_palette[i % len(color_palette)],
                "fill": True,
                "tension": 0.4,
                "pointBackgroundColor": color_palette[i % len(color_palette)],
                "pointBorderColor": '#fff',
                "pointRadius": 3,
                "pointHoverRadius": 5
            })

        year_month_choices = [(m, m) for m in unique_months]
        monthly_data = dict(overall_line)

        # カテゴリー内訳用データ（ドーナツチャート用）
        category_totals = defaultdict(int)
        for exp in filtered_data:
            cat = exp.tag or "その他"
            category_totals[cat] += exp.amount
        category_totals_data = [category_totals[cat] for cat in tags_sorted]

        return render_template(
            "index.html",
            data=filtered_data,
            unique_tags=sorted({exp.tag or "その他" for exp in [Expense(**item) for item in data]}),
            year_month_choices=year_month_choices,
            all_months=all_months_sorted,
            overall_dataset=overall_dataset,
            cat_charts=cat_charts,
            tags=tags_sorted,
            latest_month=latest_month,
            stacked_datasets=stacked_datasets,
            current_sort_order=sort_order,
            monthly_data=monthly_data,
            category_totals_labels=tags_sorted,
            category_totals_data=category_totals_data
        )
    except Exception as e:
        flash(f"エラーが発生しました: {str(e)}", "error")
        return redirect(url_for("index"))

@app.route("/edit/<record_id>", methods=["GET", "POST"])
@login_required
def edit(record_id):
    try:
        start_date_param = request.args.get("start_date", "")
        end_date_param = request.args.get("end_date", "")
        yymm_param = request.args.get("year_month", "")
        filter_tag_param = request.args.get("filter_tag", "")
        sort_order_param = request.args.get("sort_order", "asc")

        data = load_data()
        expense_data = next((item for item in data if item['id'] == record_id), None)
        if not expense_data:
            flash("対象データが見つかりません。", "error")
            return redirect(url_for("index"))

        expense = Expense(**expense_data)
        unique_tags = sorted({Expense(**item).tag or "その他" for item in data})

        if request.method == "POST":
            date_str = request.form.get("date", "")
            store_str = request.form.get("store", "")
            amt_str = request.form.get("amount", "")
            tag_str = request.form.get("tag", "")
            det_str = request.form.get("details", "")

            h_start_date = request.form.get("start_date_hidden", "")
            h_end_date = request.form.get("end_date_hidden", "")
            h_year_month = request.form.get("year_month_hidden", "")
            h_filter_tag = request.form.get("filter_tag_hidden", "")
            h_sort_order = request.form.get("sort_order_hidden", "asc")

            if date_str and store_str and amt_str:
                expense.date = date_str.strip()
                expense.store = store_str.strip()
                expense.amount = parse_amount(amt_str)
                expense.tag = automatic_tagging(store_str) if not tag_str else tag_str.strip()
                expense.details = det_str.strip()

                for item in data:
                    if item['id'] == record_id:
                        item.update(expense.to_dict())
                        break
                save_data(data)
                flash("編集を保存しました。", "success")
                return redirect(url_for("index", start_date=h_start_date, end_date=h_end_date, year_month=h_year_month, filter_tag=h_filter_tag, sort_order=h_sort_order))
            else:
                flash("必須項目が不足しています。", "error")
                return render_template("edit.html", record=expense, unique_tags=unique_tags, start_date=start_date_param, end_date=end_date_param, year_month=yymm_param, filter_tag=filter_tag_param, current_sort_order=sort_order_param)
        return render_template("edit.html", record=expense, unique_tags=unique_tags, start_date=start_date_param, end_date=end_date_param, year_month=yymm_param, filter_tag=filter_tag_param, current_sort_order=sort_order_param)
    except Exception as e:
        flash(f"エラーが発生しました: {str(e)}", "error")
        return redirect(url_for("index"))

@app.route("/delete/<record_id>", methods=["POST"])
@login_required
def delete(record_id):
    try:
        data = load_data()
        new_data = [item for item in data if item['id'] != record_id]
        if len(new_data) != len(data):
            save_data(new_data)
            flash("削除しました。", "success")
        else:
            flash("削除対象が見つかりません。", "error")
        return redirect(url_for("index"))
    except Exception as e:
        flash(f"エラーが発生しました: {str(e)}", "error")
        return redirect(url_for("index"))

@app.route("/api/plot_detail", methods=["POST"])
@login_required
def plot_detail():
    try:
        req_data = request.get_json()
        if not req_data:
            return jsonify({"error": "データがありません"}), 400

        selected_month = req_data.get("month", "")
        selected_tag = req_data.get("tag", "")

        if not selected_month:
            return jsonify({"error": "月が指定されていません"}), 400

        data = [Expense(**item) for item in load_data()]

        if selected_tag == "Overall":
            tag_totals = defaultdict(int)
            for expense in data:
                if expense.date.startswith(f"{selected_month}-"):
                    tag_totals[expense.tag or "その他"] += expense.amount
            result_list = [{"tag": tag, "amount": amt} for tag, amt in tag_totals.items()]
        else:
            store_totals = defaultdict(int)
            for expense in data:
                if expense.date.startswith(f"{selected_month}-") and expense.tag == selected_tag:
                    store_totals[expense.store] += expense.amount
            result_list = [{"store": store, "amount": amt} for store, amt in store_totals.items()]

        return jsonify({"detail": result_list})
    except Exception as e:
        return jsonify({"error": f"エラーが発生しました: {str(e)}"}), 500

if __name__ == "__main__":
    load_data()  # データファイルが存在しない場合に備える
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
