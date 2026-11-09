# ReliefRoute Arena

災害時の救援物資の配送を題材に、戦略を実行・比較し、結果を地図で振り返るシミュレーションプラットフォームです。

**Hachimitsu · DevFest GDGoC Japan Hackathon 2026 · オンライン会場 · 医療・福祉**

既存デモ: https://reliefroute-arena-293373083050.asia-northeast1.run.app

> 公開デモは旧版です。この提出候補のデプロイとクラウド構成の最終検証は未実施です。機能の説明は本リポジトリのコードを対象とします。

## プロジェクト概要

利用者が配送方針を設定し、同じ条件で複数の Bot を比較します。道路封鎖、渋滞、需要増加のある架空の環境で、配送量だけでなく期限、公平性、資源効率を確認できます。**教育・戦略研究用の仮想環境であり、実際の救援指揮や医療判断には使用しません。** 実際の災害情報や個人情報は扱いません。

## 背景・解決したい課題

限られた車両と物資をどこに配分するかによって、全体の配送量と支援の公平性は変わります。初学者や学習会の参加者が、コードを書かなくても方針を比較し、その結果を説明できる環境を目指しています。利用者調査による効果検証は未実施です。

## 提案するアプローチ

共通の観測・行動プロトコル、固定 seed、決定的なエンジンと採点を用います。ルールによる Bot と Dijkstra 型の最短経路計算を組み合わせ、同じ条件なら同じ結果を再現します。LLM は意思決定や採点に使用しません。

## 主な機能

| 機能 | メインアリーナ | 時間別リーグ |
| --- | --- | --- |
| シナリオ | 基本・イベント、seed を指定 | UTC の時間帯から生成 |
| 規模 | 倉庫 1、避難所 3、車両 3、24 ターン | 倉庫 1、避難所 6、車両 5、道路 11、48 ターン |
| Bot | 近距離優先、緊急度優先、パラメーター戦略 | パラメーター戦略、制限付きコード Bot |
| 比較 | 3 戦略 × 公開 seed 3 個の 9 試合 | 同じ時間帯の参加 Bot による対戦 |
| 保存 | JSON をダウンロード | Bot・順位ポイント・結果を保存。完全なリプレイは最新ラウンドのみ |

- 地図の再生・一時停止、コマ送り、速度変更、タイムライン移動、施設・車両・道路の詳細表示。
- 日本語を初期表示とし、中文・English に切替可能。保存済みの選択を優先します。
- 3 種類の環境 × 3 種類の安定した配置による九つの**視覚レイアウト**。九つの物理災害モデルではなく、配置の変更は輸送時間や採点を変えません。
- 総合スコアと C（需要充足）、T（期限内配送）、F（公平性）、E（資源効率）を表示。重みは 60/20/15/5、採点バージョンは 0.1 です。

## システム構成

ブラウザー → Python HTTP/WSGI API → Bot・シミュレーション・採点 → JSON リプレイという構成です。ページと API を同じオリジンで提供します。リーグの定期実行は Web リクエストから分離します。[構成図](docs/21-architecture.md)を参照してください。

## 使用技術

Python 標準ライブラリ、HTML/CSS/JavaScript、SVG、SQLite、Gunicorn、Google Cloud Storage Python SDK を使用します。フロントエンドのビルドや npm 依存はありません。コード Bot は AST を逐次解釈する制限付き決定言語であり、完全な Python サンドボックスではありません。

## Google Cloud の活用

| 技術 | 製品での役割 | 検証状態 |
| --- | --- | --- |
| Cloud Run Service | ページ、API、オンライン模擬配送と採点 | 旧版は公開稼働。候補版は未デプロイ |
| Cloud Storage | 私有オブジェクトにリーグの SQLite スナップショットを保存 | 実装済み。実際の Bucket/IAM は最終検証待ち |
| Cloud Run Jobs | 時間帯ごとの対戦・順位更新 | 入口・設定済み。実環境の設定と実行ログは検証待ち |
| Cloud Scheduler | 毎時の Job 起動 | スクリプト対応。実際のトリガーは検証待ち |
| Cloud Build / Artifact Registry | コンテナー構築・保存 | ソースデプロイで使用する構成。最終ビルド証跡は次段階 |
| IAM / サービスアカウント | ストレージアクセスと Job 呼出しを分離 | スクリプトに最小権限構成。実際の付与状態は検証待ち |

ローカル PC に依存しない公開環境、周期的な対戦、結果の保存、同一イメージによる再現性を支えます。スクリプトの存在を稼働証明とは扱いません。**Gemini / Vertex AI は製品の実行経路に接続していません。** Google Maps、Firestore、Firebase も未使用です。

## セットアップ

Python 3.9 以上を用意してください（今回の検証は Python 3.13）。ローカル実行には標準ライブラリのみを使います。Node.js は JS テスト用で、サイトの起動には不要です。Linux の本番コンテナーは Python 3.13 と `requirements.txt` の依存を使います。

## ローカル実行方法

リポジトリのルートで実行します。Windows は `python`、macOS/Linux では必要に応じて `python3` を使用してください。

macOS / Linux:

```bash
python3 -m reliefroute.server
```

Windows PowerShell:

```powershell
python -m reliefroute.server
```

以下の例は `python` 表記です。macOS / Linux ではインストール済みの Python 3 を指す `python3` に読み替えてください。

- アリーナ: http://127.0.0.1:8000/
- リーグ: http://127.0.0.1:8000/league
- 既定の待受けは `127.0.0.1:8000` のみ。終了は Ctrl+C。
- ポート変更: `python -m reliefroute.server --port 8002`。その場合は上記 URL の `8000` を `8002` に変更します。
- 初回は日本語。選択言語は同一オリジンの `localStorage`（`reliefroute.language`）に保存し、更新・ページ移動後も優先します。別ポートや別ドメインは別設定です。保存できない環境ではそのページ内で切り替えられます。

初回起動で必要なディレクトリと SQLite のテーブルを自動初期化します。SQLite は `outputs/local-league.sqlite3` に保存され、再起動後も Bot・順位ポイント・結果を保持します。空の順位表は正常な初期状態です。指定優先度は `--db`、`RELIEFROUTE_LEAGUE_DB`、既定パスの順です。相対パスは起動ディレクトリが基準です。ローカル入口は継承した `RELIEFROUTE_LEAGUE_BUCKET` を無視します。

通常起動は Bot 登録・対戦結算・定期実行を行いません。別ターミナルで `python scripts/local_league.py --once` を実行すると現在の UTC 時間帯を一度結算します。新規・再開 Bot は次の時間帯から参加します。別の DB を使う場合は両コマンドに同じ `--db` を指定してください。

```bash
# 独立した試用データでデモ Bot と最初の対戦を用意する
python scripts/local_league.py --demo --db outputs/demo.sqlite3 --port 8016
```

カスタム DB の例: `python -m reliefroute.server --db outputs/my-league.sqlite3`。上の Demo は http://127.0.0.1:8016/league で開けます。Demo の登録条件、同一時間帯の再実行、継続 worker は [リーグ利用ガイド](docs/23-hourly-league.md)を参照してください。

## デプロイ構成

Cloud Run Service と Job が同じイメージ digest と私有 Cloud Storage を使い、Scheduler が毎時 Job を呼び出します。Cloud Run の一時ファイルを永続 DB として使いません。[デプロイ](docs/16-deployment.md)と[リーグ構築手順](docs/25-league-deployment.md)を参照してください。本段階ではクラウドを変更していません。

## 操作ガイド

1. アリーナでシナリオ、seed、Bot または三つの戦略パラメーターを選び、試合を実行します。
2. 最終スコアと配送統計を確認し、リプレイで各ターンの状態を振り返ります。最終スコアは再生位置の途中スコアではありません。
3. 戦略比較で九つの結果を確認し、結果から対応する試合を再生します。JSON は保存・再採点できます。
4. リーグでは Bot を登録し、一度だけ表示される管理トークンを私的に保存します。次の時間帯の結算後、順位と試合を確認します。
5. コード Bot はサンプルから作成します。変更は新規 Bot 登録となり、順位ポイントを引き継ぎません。

詳細: [リーグ利用ガイド](docs/23-hourly-league.md) / [コード Bot](docs/24-code-bots.md)。

## CLI による実行・記録・再採点

```bash
# イベントのない回帰用シナリオ
python -m reliefroute
# イベントあり、固定 seed、JSON 記録の保存
python -m reliefroute --scenario events --seed 11 --bot urgency --output outputs/match.json
# 完全な試合記録から再採点（保存済み score は使用しない）
python -m reliefroute --rescore outputs/match.json
# 参考 Bot 2 種 × seed 11/22/33 の6試合
python -m reliefroute --compare --output outputs/comparison.json
# パラメーター戦略を加えた3戦略・9試合
python -m reliefroute --compare --config examples/fair-strategy.json
python -m reliefroute --scenario events --seed 22 --bot custom --config examples/fair-strategy.json --output outputs/custom.json
python -m reliefroute --rescore outputs/custom.json
```

`--output` は親ディレクトリも作成します。比較レポート全体は単一試合のリプレイではないため `--rescore` に渡しません。再採点は信頼できる完全なエンジン記録の検証用であり、改ざんされた外部提出の真正性を保証しません。[エンジン・採点・リプレイの技術ガイド](docs/30-technical-guide-ja.md)に記録形式と制限をまとめています。

## テスト・検証

```bash
python -m unittest discover -s tests -q
# tests/*.cjs の全 9 スクリプトを Node.js で実行する
node tests/frontend_replay.cjs
node tests/language_detection.cjs
node tests/design_summary.cjs
node tests/league_autowatch.cjs
node tests/league_geometry.cjs
node tests/league_interactions.cjs
node tests/map_interactions.cjs
node tests/map_layouts.cjs
node tests/replay_controller.cjs
python scripts/manifest.py --check
```

検証対象と結果、モバイル表示、未検証項目は[受入記録](docs/18-mvp-acceptance.md)にまとめています。更新時は `python scripts/manifest.py` でファイル一覧を再生成します。

## 制約事項

- 小規模の架空環境であり、現実の災害対応の有効性を証明しません。
- リーグは初期 1000 点、各ラウンド最大 ±16 点の順位ポイントで、Elo ではありません。
- 完全なリプレイは最新ラウンドのみ。過去の全試合閲覧、アカウント復旧、外部 HTTPS Bot は未対応です。
- 登録は合計 100 Bot まで。これは容量制限であり、不正登録や大量アクセスへの完全な対策ではありません。
- クラウドスナップショットは小規模試用向けです。すべての履歴をリプレイとして保持せず、高負荷保証もありません。

## 今後の展望

利用者による学習効果の確認、評価シナリオの拡充、公開運用時の登録管理と容量測定を今後の検討事項とします。今回の候補版への追加機能ではありません。

## ライセンス

プロジェクト固有のコードとドキュメントは [MIT License](LICENSE) で公開します。著作権表示は公式提出先の `Copyright (c) 2026 The contributors of this repository` を保持します。第三者のコード・素材にはそれぞれのライセンスが適用されます。[依存・素材一覧](docs/22-asset-inventory.md)を参照してください。

## 提出情報・文書

提出締切は **2026 年 11 月 10 日 19:00 JST**。オンライン会場は指定 Google Docs、デモを含む 5 分以内の MP4、指定著作物利用シート、公式 GitHub が必要です。資料は一つの Drive フォルダーにまとめ、フォームを送信します。締切後から 11 月 14 日終了まで実行環境を凍結・維持します。

- [提出原稿](docs/19-submission-draft-ja.md) / [短い紹介](docs/09-pitch-ja.md)
- [公式提出先](https://github.com/Devfest-Hackathon-2026/df-2026-t049)
- [公式提出ルール](https://docs.google.com/document/d/1r2QRvMQbcJqhmYAEKAFTN9Co_zsJzvFhxfuS1wx1FJE/edit)
- 初期設計・過去の受入記録は `docs/` に保存しています。過去時点の完了数・構成は現在の仕様を表すものではありません。

## 公式提出リポジトリ

運営の提出案内は [SUBMISSION-GUIDE.md](SUBMISSION-GUIDE.md) に保持しています。このリポジトリでは GitHub Actions / Pages を使用しません。回帰テストはローカルで実行します。

## 詳細文書の案内

| 読みたい内容 | 文書 |
| --- | --- |
| 現行エンジン、Bot 契約、採点式、地図とリプレイ | [技術ガイド](docs/30-technical-guide-ja.md) |
| DB、Demo、手動結算、管理トークン | [時間別リーグ](docs/23-hourly-league.md) |
| コード例と制限付き言語 | [コード Bot](docs/24-code-bots.md) |
| モジュールと永続化 | [構成](docs/21-architecture.md) |
| ローカルと本番、検証手順 | [デプロイ](docs/16-deployment.md) / [リーグ運用](docs/25-league-deployment.md) |
| 実測結果・未完了事項 | [受入記録](docs/18-mvp-acceptance.md) |
| 第三者ライセンス | [依存・素材一覧](docs/22-asset-inventory.md) |

初期設計と中国語の開発記録も保持しています。現行仕様との対応と読む際の注意は技術ガイド末尾に記載しています。
