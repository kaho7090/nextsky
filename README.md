# nexttrip

NextTrip helps travellers discover unvisited countries and plan efficient trips.

## 概要

NextTrip は、**197カ国**を訪問目標として、未訪問国を優先度（0〜5）でランキングし、訪問済み国を記録する Streamlit アプリです。国マスタは同梱 CSV、個人の訪問状況・優先度は SQLite に保存します（実行時の外部 API は使いません）。

## 対象国（197カ国）の定義

デフォルトの訪問目標は次の集合です。

- 国連加盟国 193カ国
- 国連オブザーバー: バチカン市国（`VA`）、パレスチナ（`PS`）
- 追加: 台湾（`TW`）、コソボ（`XK`）

正準リストは `data/target_countries.csv`（`code` 列）および `src/nexttrip/targets.py` の `DEFAULT_TARGET_COUNTRY_CODES` で定義します。ランキング・訪問管理 UI・地図の「対象」はこの197カ国に限定されます。

`data/countries.csv` は国・地域マスタ（約250件）として維持し、197件には削減しません。対象外の国・地域に保存済みの訪問状況・優先度は削除しません。

### コソボ（`XK`）について

`XK` は ISO 3166-1 の正式な alpha-2 割当ではありませんが、本アプリではコソボを識別する内部コードとして使用します。Natural Earth の GeoJSON では `ISO_A2_EH` が `XK` の地物にマッピングします。

## 技術スタック

- Python 3.12
- Streamlit
- SQLite
- pandas
- Plotly（コロプレス地図）
- pytest

## セットアップ

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## 起動

```bash
streamlit run src/nexttrip/app.py
```

ブラウザで UI が開きます（表示言語は日本語）。

## テスト

```bash
pytest
```

## Travelport 航空券検索（トライアル）

Streamlit の「航空券検索」タブから片道検索できます。認証情報は次のいずれかで設定します（`.env.example` を参照）。

1. リポジトリルートの `.env`（起動時に自動読み込み。既存のシェル環境変数は上書きしません）
2. シェルの `export`
3. `.streamlit/secrets.toml`（未設定のキーのみ補完）

接続準備の確認（実 API は呼びません）:

```bash
python -c "import json; from nexttrip.flights.env_loader import travelport_readiness_report as r; print(json.dumps(r(), indent=2, ensure_ascii=False))"
```

- OAuth（プレプロダクション既定）: `https://auth.pp.travelport.net/oauth/token`
- Search API: `https://api.pp.travelport.net/11/air/catalog/search/catalogproductofferings`
- GDS 指定: `contentSourceList: ["GDS"]`
- Fare Calculation 要求: `CustomResponseModifiersAir.includeFareCalculationInd: true`

本番エンドポイントには自動切り替えしません。予約・発券はスコープ外です。

## データ

| ファイル | 内容 |
|----------|------|
| `data/countries.csv` | 国・地域マスタ（英語名・日本語名） |
| `data/target_countries.csv` | 訪問目標197カ国のコード一覧 |
| `data/geo/ne_50m_admin_0_countries.geojson` | 世界地図用国境データ（Natural Earth） |
| `data/nexttrip.db` | 訪問状況・優先度（初回起動時に自動作成、git 管理外） |

### 地図データの出典

国境 GeoJSON は [Natural Earth](https://www.naturalearthdata.com/) の **Admin 0 – Countries**（50m 解像度）を加工せず同梱しています。

- 出典: Natural Earth / nvkelso/natural-earth-vector
- ライセンス: [Public Domain](https://www.naturalearthdata.com/about/terms-of-use/)

地図タイルや外部 URL からの実行時取得は行いません。

## プロジェクト構成

```text
src/nexttrip/   アプリ本体（DB・ランキング・地図・Streamlit）
data/              国マスタ・対象国リスト・GeoJSON・SQLite
tests/             pytest
```

## 改名について（2026-11-05）

旧称 NextCountry から **NextTrip** に統合改名した。197カ国の訪問管理（Country の役割）と運賃探索（Fare の役割）を1つのプロダクトに束ねるための改名で、パッケージ名も `nexttrip` に統一している。なお、既存の訪問・優先度データを保持するため、SQLite のファイル名は当面 `data/nextcountry.db` のまま据え置く。
