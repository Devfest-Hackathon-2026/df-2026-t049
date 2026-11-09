# 提出候補の受入記録

## 対象と目的

検証日: 2026-11-09 JST。基準コミット: `8974761900bb484a5b9318f100c68abd3ae7a7f5`。作業ブランチ: `release/hackathon-submission-prep`。基準に日本語文書整理、表示用エラー文言、既存 CI のテスト追加を適用した候補を検証しました。Bot、経路計算、シナリオ、採点、API の構造・データ形式は変更していません。

古い完了数やデプロイ記録は[過去の記録](history/18-mvp-acceptance-before-release.md)に保存しています。本ページの今回実測と区別してください。

## 今回の自動検証

| 対象 | コマンド | 結果 |
| --- | --- | --- |
| Python | `python -B -m unittest discover -s tests -q` | 63 テスト成功（Python 3.13、Windows） |
| アリーナリプレイ | `node tests/frontend_replay.cjs` | 44 試合、9504 車両・フレーム・環境ケース成功 |
| 言語 | `node tests/language_detection.cjs` | 日本語既定、保存設定、保存不可時、時刻境界を確認 |
| 比較 | `node tests/design_summary.cjs` | 同点、欠損指標、入力不変を確認 |
| 自動観戦 | `node tests/league_autowatch.cjs` | 空状態、手動選択優先、古い応答、失敗後を確認 |
| リーグ地図 | `node tests/league_geometry.cjs` | 1440 車両フレーム成功 |
| リーグ操作 | `node tests/league_interactions.cjs` | トークンコピー、日中英の登録エラー、未知診断の保持、送信/成功データ不変を確認 |
| 地図操作 | `node tests/map_interactions.cjs` | クリック、キーボード、選択、イベント巻戻しを確認 |
| 九配置 | `node tests/map_layouts.cjs` | 13608 車両フレーム、配置とイベント表示を確認 |
| 再生時計 | `node tests/replay_controller.cjs` | 一時停止、再開、時刻リセット、背景時制限を確認 |
| JS 構文 | `node --check web/league.js` / `node --check web/i18n.js` | 成功 |
| ソース一覧 | `python scripts/manifest.py` の後 `--check` | 92 ファイルを再生成・照合、成功 |

JS は全 9 スクリプトで、今回の表示修正の検証は既存 league_interactions に追加しました。テスト削除や期待値の緩和はしていません。ローカル HTTP と一時 DB を使う Python テストは、それらを利用できる実行環境で確認しました。

## 今回のブラウザー検証

独立 DB `outputs/release-review.sqlite3`、ローカル 8032 番ポートを使用し、既存データとクラウドを変更していません。

- 保存済み設定のないページで日本語が選択されることを確認。
- 390 × 844 のアリーナ、九試合比較、リーグ、コード入力欄を確認。ページ幅の横はみ出しなし（viewport 390、document scrollWidth 375）。表・コード欄の内部スクロールは許容。
- 実際の九試合比較から試合を開き、再生・一時停止を操作。
- 空白 Bot 名の拒否を日本語で表示。コード例の読込みとエディターを確認。
- `python -B scripts/local_league.py --demo --once --db outputs/release-review.sqlite3` により、明示的に二つのローカル試用 Bot と本物の試合を生成。順位と 48 ターンのリプレイ、末尾 47/47 を確認。
- 中文、English、日本語の切替と英語選択後のリロード保持を確認し、最後は日本語へ復帰。
- 1280 × 900 のリーグを確認。横はみ出しなし（scrollWidth 1265）。取得したブラウザーログに warning/error なし。
- レイアウトや CSS の変更は不要でした。スクリーンショットはローカル outputs に保存し、提出ソースに含めません。

## 機能・クラウドの状態

主アリーナ、リーグ、二種類の登録方式、順位ポイント、九視覚配置、三言語、地図・車両リプレイを実装済みです。スコアと途中状態、最新リプレイと古い結果の要約を区別します。

第一段階で公開 URL の健康・試合・リーグ・既存リプレイを確認しましたが、公開静的ファイルは基準 main より古い版です。今回、クラウドには変更していません。Bucket/IAM、Job 実行ログ、Scheduler 実トリガー、最終 image digest と revision、継続稼働は独立検証待ちです。GitHub の基準 main CI 成功は、今回の未 Push ブランチの CI 実行とは区別します。

## 文書・差分の確認

更新文書と移動した履歴の相対リンク 29 件を検査し、参照先の欠落なし。`git diff --check` 成功。`reliefroute/`、デプロイスクリプト、依存宣言、Dockerfile、Gunicorn 設定に変更なし。公式の秘密ファイル除外項目を `.gitignore` に追加し、ローカル outputs は引き続き対象外です。

## 提出前に残る事項

B1 で MIT 表記統一と公式候補コード同期（`7cc87a9`）を完了しました。残る必須事項: 最終候補のクラウド検証・デプロイ、指定資料と MP4、Drive 権限、フォーム提出。締切は 2026-11-10 19:00 JST。以降 11 月 14 日終了まで環境を凍結・維持します。

推奨: 最終イメージの OS/推移的依存一覧と脆弱性確認、登録枠・費用・スナップショット容量確認。完全な公開サービスの不正登録対策や大規模運用は今回保証しません。

[README](../README.md) / [構成](21-architecture.md) / [依存・権利](22-asset-inventory.md)

## 文書完全性の追加検証（2026-11-10 JST）

公式候補 `7cc87a9` を基準に、初期 README（`84e48318`）、開発 main（`8974761`）、日本語整理（`9353dae`）、MIT 統一後の開発源（`4c38c72`）を比較しました。ローカル起動・DB・Demo・CLI・再採点・採点式・描画境界を日本語で補足し、旧設計は歴史資料として保持しました。プログラム、Bot、採点、API、依存は変更していません。

- `python -m unittest discover -s tests -q`：63 件成功（Windows / Python 3.13）。
- README の基本 CLI、events/urgency と custom の JSON 出力・`--rescore` 一致、比較 6 試合と設定追加時 9 試合を実行確認。
- 隔離した一時 DB で `--demo --once`、続く `--once` を確認。Bot 2 件・完了ラウンド 1 件で重複加点なし。
- 標準ポート 8000、`--port 8002`、Demo の 8016 で `/health`、`/`、`/league`、`/api/league` が成功。8002 への `scripts/smoke.py` も成功。
- `node tests/language_detection.cjs`：日本語既定、保存設定、保存不可時、時刻・実 ID の検証成功。全9本の JS スクリプトは B1 で成功済み。本輪は表示コードを変更していないため全件は再実行していません。
- 検証用コード自身の SQLite 接続が一時ファイル削除を妨げたため、接続を閉じて命令検証を再実行し、後片付けまで成功しました。製品テストの期待値は変更していません。
- macOS/Linux 実機、Python 3.9 実機、Docker、クラウドでの今回実行はしていません。`python3` は同じモジュール入口を呼ぶコマンド表記として確認しました。

本輪は B2/B3、クラウド変更、ビルド、デプロイ、フォーム送信を行っていません。
