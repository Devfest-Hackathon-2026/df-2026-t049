# クラウドの時間別リーグ構築

## 状態

構築コードは実装済みです。第一段階では既存公開 API に二つの Bot と各 19 試合、48 フレームのリプレイがあることを確認しました。しかし、これだけでは Scheduler、Job、Bucket、IAM の設定や自動実行を証明できません。候補版デプロイと実リソースの確認は次段階です。

## 構築入口（次段階で実行）

認証済み Cloud Shell で、確定した候補コミットのリポジトリルートから実行します。

```bash
python3 scripts/deploy_league.py YOUR_PROJECT_ID --region asia-northeast1
```

このコマンドは実際のクラウドリソースを作成・更新し、最後に Job を一度実行します。確認だけのコマンドではありません。プロジェクトと結算の確認を済ませてから使います。スクリプトは明示的な project 引数を使い、グローバル設定を変更しません。

## スクリプトの処理

1. Run、Build、Artifact Registry、Storage、Scheduler、IAM API を有効化。
2. 実行用 `reliefroute-league` と起動用 `reliefroute-clock` サービスアカウントを用意。
3. `<project>-<project-number>-league` Bucket を作成。統一 IAM と公開アクセス防止を設定。
4. 実行用アカウントに、その Bucket の `roles/storage.objectAdmin` を付与。
5. `reliefroute-arena` をソースから構築・公開。1 CPU、1 GiB、最小 0/最大 2 インスタンス、並行数 2、120 秒タイムアウト。
6. Ready revision の digest を取得し、同じイメージの `reliefroute-hourly` Job を設定。単一 task、並行数 1、再試行 1、600 秒、1 CPU/1 GiB。
7. 起動用アカウントに当該 Job の `roles/run.invoker` を付与。
8. Scheduler を `0 * * * *` / `Etc/UTC` に設定し、OAuth で Run Jobs API を呼出し。
9. Job を一度実行して終了を待ち、公開 URL を表示。

構築主体には適切なデプロイ・ビルド・サービスアカウント利用権限が必要です。Owner を一括付与する手順ではありません。既存リソースの実際の権限・公開防止設定は別途確認します。

## 最終検証項目

- Service と Job の digest、Git SHA、環境変数が一致する。
- 未ログインで `/health`、`/`、`/league`、模擬試合とリプレイを確認できる。
- パラメーター Bot とコード Bot を登録し、次の UTC 整点に Scheduler による実行が成功する。
- 実行ログ、試合数、順位ポイントと完全リプレイを照合する。
- 同時間帯の再実行で重複加点されず、不正トークンでは停止できない。
- 凍結前にインスタンス切替後もデータが残ることを確認する。
- Bucket は非公開であり、ソースコード・管理トークンのハッシュを公開しない。
- 登録上限、スナップショット容量、実行時間、費用を確認する。100 Bot 制限は不正登録対策ではない。

クラウドスナップショットは gzip 保存、解凍上限 128 MiB、generation による競合検出を行います。古い非対応イメージへの巻き戻しは避けます。Bucket の soft delete 等の保持設定は、画面上のリプレイ保持範囲とは別です。

[定時 Job 実行](https://docs.cloud.google.com/run/docs/execute/jobs-on-schedule) / [デプロイ・凍結](16-deployment.md)
