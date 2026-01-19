
# 首先：「確保程式無論在誰的電腦上執行，都能正確找到資料夾位置，並設定好中文字型。」
from pathlib import Path  ### TBD。

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# 路徑設定（pathlib.Path　是路徑處理工具）
BASE_DIR = Path(__file__).resolve().parent      # notebooks/　程式碼所在的資料夾。
ROOT_DIR = BASE_DIR.parent                      # testRepo/　上一層專案根目錄。
DATA_DIR = ROOT_DIR / "data"                    # 定義資料存放與圖片輸出的位置。
IMG_DIR = ROOT_DIR / "images"
IMG_DIR.mkdir(exist_ok=True)                    # 檢查 images 資料夾是否存在，如果不存在就自動建一個，避免儲存圖片時報錯。
FILE_PATH = DATA_DIR / "cpi_taiwan.csv"

# 字型設定；使用正體中文，微軟正黑體
plt.rcParams["font.sans-serif"] = ["Microsoft JhengHei"]
plt.rcParams["axes.unicode_minus"] = False      # 解決坐標軸負號（-）顯示不正常的問題。

# 資料處理
def roc_to_datetime(roc_str: str) -> pd.Timestamp:
    """'109年1月' -> Timestamp('2020-01-01')"""
    roc_year = int(roc_str.split("年")[0])
    month = int(roc_str.split("年")[1].replace("月", ""))
    ad_year = roc_year + 1911
    return pd.to_datetime(f"{ad_year}-{month:02d}-01") # d=整數；02=至少2位數，不足補0。


def load_and_clean_cpi(file_path: Path) -> pd.DataFrame:
    # 第3列當欄位名稱
    df = pd.read_csv(file_path, header=2) # 用來讀取CSV。

# 去掉多餘欄
    # loc 是用來定位資料的，冒號: 代表「所有的列」，逗號後面則是選取「哪些欄」。
    # ~：代表「不要、非」的意思。
    # str.contains("^Unnamed")：找尋欄位名稱中包含「Unnamed」的（這通常是 CSV 讀取時產生的空白欄位）。
    # 總結：這兩行是在說「保留不包含 Unnamed 和不包含指數基期的欄位」。
    # df.columns.str.contains是在檢查**「標題」**。
    df = df.loc[:, ~df.columns.str.contains("^Unnamed")]  
    df = df.loc[:, ~df.columns.str.contains("指數基期")]

 # 只保留像「109年1月」的列
    # \d 代表「數字」，找格式長得正好是「數字+年+數字+月」的資料。
    # .copy()：安全習慣，代表把篩選出來的東西複製一份來處理，不會影響到原始的df。
    mask = df["統計期"].astype(str).str.match(r"^\d+年\d+月$", na=False)
    df_monthly = df[mask].copy()

    # 轉date
    # .apply(roc_to_datetime): 重要的連結！表示「把統計期這欄的每個格子，都丟進剛才寫好的roc_to_datetime翻譯機裡跑。」
    # 最後把翻譯出來的西元日期存進一個新欄位叫date。
    df_monthly["date"] = df_monthly["統計期"].apply(roc_to_datetime)

    return df_monthly



def to_long(df_monthly: pd.DataFrame) -> pd.DataFrame:
    df_long = df_monthly.melt(
        id_vars=["date"],
        value_vars=[c for c in df_monthly.columns if c not in ["統計期", "date"]],
        var_name="分類",
        value_name="指數"
    )
    return df_long


# 繪圖
def plot_cpi(df_long: pd.DataFrame, categories: list[str], output_path: Path) -> pd.DataFrame: #這個是什麼? 為什麼從NONE改pd.DataFrame?
    # =========================
    # 指數化：基準期 = 100 
    # # 1. 設定基準期
    base_date = pd.to_datetime("2021-04-01")  # 想換參照點就改這行

    # 算出每個分類在 base_date 的基準值
    # # 2. 計算指數化 (使用 map 較優)
    base_values = (
        df_long[df_long["date"] == base_date]
        .set_index("分類")["指數"]
    )
    
    # 用 map 比 apply 快且乾淨
    df_long = df_long.copy()
    df_long["base"] = df_long["分類"].map(base_values)
    df_long["index_100"] = (df_long["指數"] / df_long["base"]) * 100
    

    # 指數化算完後，再篩選要畫的分類
    # # 3. 篩選與排序
    df_plot = df_long[df_long["分類"].isin(categories)].copy()
    df_plot = df_plot.sort_values("date")

    fig, ax = plt.subplots(figsize=(11, 6))

    # 4. 繪圖 (這裡要畫 index_100)
    for cat in categories:
        data = df_plot[df_plot["分類"] == cat]
        ax.plot(data["date"], data["index_100"], label=cat, linewidth=2)


    # 美化
    ax.grid(True, which="major", axis="y", linestyle="--", linewidth=0.8, alpha=0.4)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # 基準線 (100)
    ax.axhline(100, color='red', linestyle='-', linewidth=1, alpha=0.5)

    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    fig.autofmt_xdate(rotation=0)

    ax.set_title(f"台灣 CPI：主要類別走勢 (基準期：{base_date.strftime('%Y-%m')}=100)", pad=12)
    ax.set_ylabel("指數化數值")
    ax.legend(title="分類", loc="center left", bbox_to_anchor=(1.02, 0.5), frameon=False)


    # ax.set_title("台灣 CPI：主要類別走勢（指數化，基準期=100）", pad=12)
    # ax.set_xlabel("月份")
    # ax.set_ylabel("指數化（基準期=100）")
    # ax.legend(title="分類", loc="center left", bbox_to_anchor=(1.02, 0.5), frameon=False)



    # =========================
    # 關鍵事件註解
    # =========================
    # events: (日期, 顯示文字, 對齊哪一條線的分類)
    events = [
            ("2020-02-01", "COVID-19 爆發初期", "總指數"),
            ("2022-03-01", "2022年2月24日 俄烏侵略戰爭爆發\n能源/運輸成本波動", "四.交通及通訊類"),
        ]


    # for date_str, label, anchor_cat in events:
    #         event_date = pd.to_datetime(date_str)

    #         # 取該日期、該分類的 y 值（確保註解對準線）
    #         s = df_plot[(df_plot["分類"] == anchor_cat) & (df_plot["date"] == event_date)]["index_100"]
    #         if s.empty:
    #             # 如果這個月資料不存在，就跳過（避免程式報錯）
    #             continue

    #         y = float(s.iloc[0])

    #         # 先畫一條淡淡的垂直線，幫讀者定位時間點
    #         ax.axvline(event_date, linestyle="--", linewidth=1, alpha=0.35)

    #         # 再放文字與箭頭
    #         ax.annotate(
    #             label,
    #             xy=(event_date, y),  # 這個以後可以沿用
    #             xytext=(event_date + pd.Timedelta(days=90), y + 6),   # y+6:往上移一點，避免蓋到線。days=90:往右3個月
    #             arrowprops=dict(arrowstyle="->", linewidth=1, alpha=0.6),
    #             fontsize=10,
    #             ha="center",  # horizontal alignment 
    #             va="bottom",  # vertical alignment
    #         )


    for date_str, label, anchor_cat in events:
        event_date = pd.to_datetime(date_str)
        s = df_plot[(df_plot["分類"] == anchor_cat) & (df_plot["date"] == event_date)]["index_100"]
        if not s.empty:
            y = float(s.iloc[0])
            ax.axvline(event_date, linestyle="--", linewidth=1, alpha=0.3)
            ax.annotate(
                label,
                xy=(event_date, y),
                xytext=(15, 15), # 座標位移
                textcoords="offset points",
                arrowprops=dict(arrowstyle="->", alpha=0.6),
                fontsize=10
            )



    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.show()

    return df_plot # 回傳 dataframe 讓 main 可以印出資訊


def main():
    df_monthly = load_and_clean_cpi(FILE_PATH)          
    df_long = to_long(df_monthly)

    target_categories = [
        "總指數",
        "一.食物類",
        "三.居住類",
        "四.交通及通訊類"
        ]

    output_path = IMG_DIR / "cpi_indexed_2021_04.png"
    df_plot = plot_cpi(df_long, target_categories, output_path)  # WHY: 為什麼這兩行不能移上去啊?
    print(df_plot[df_plot["date"] == pd.to_datetime("2020-01-01")][["分類","index_100"]])

    # 接收回傳的 df_plot
    df_result = plot_cpi(df_long, target_categories, output_path)
   
    
    # 印出基準日的檢驗資料 (應該都要是 100)
    print("\n--- 基準日資料檢驗 ---")
    print(df_result[df_result["date"] == "2021-04-01"][["分類", "index_100"]])

    if __name__ == "__main__":
        main()


    # output_path = IMG_DIR / "cpi_indexed_2021_04.png"
    # plot_cpi(df_long, target_categories, output_path)  # WHY: 為什麼這兩行不能移上去啊?
    # print(df_plot[df_plot["date"] == pd.to_datetime("2020-01-01")][["分類","index_100"]])


    # if __name__ == "__main__":
    #     main()

