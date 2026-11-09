# デプロイと運用境界

## 現在の状態

既存 URL: https://reliefroute-arena-293373083050.asia-northeast1.run.app

2026-11-09 の第一段階で、匿名 HTTP により健康状態、模擬試合、リーグ、既存リプレイを確認しました。ただし静的ファイルは基準 `8974761` と一致せず、旧版です。今回の候補版はまだデプロイしていません。過去の revision を最終版の証拠として使いません。

## ローカルと本番の違い

- ローカル: `python -m reliefroute.server`。ループバックアドレスのみ、SQLite を初期化。定期集計は別プロセスです。
- 本番: `gunicorn --config gunicorn.conf.py reliefroute.wsgi:application`。`0.0.0.0:$PORT` で待受け、非 root のコンテナーを実行します。
- Cloud Run Service はページ、API、模擬配送と採点を提供します。
- Cloud Run Job は `python -m reliefroute.league_job` を実行し、Scheduler が UTC 毎正時に起動します。
- Service と Job は同じイメージ digest と私有 GCS Bucket を使います。

## 環境変数

| 変数 | 用途 |
| --- | --- |
| `PORT` | Cloud Run が渡す HTTP ポート。既定 8080 |
| `RELIEFROUTE_LEAGUE_BUCKET` | 本番リーグの私有スナップショット Bucket。DB 指定より優先 |
| `RELIEFROUTE_LEAGUE_DB` | ローカル等の永続 SQLite パス。本番 Cloud Run の一時領域を正本にしない |

WSGI で両ストレージ変数がない場合、リーグ API は 503 を返します。ローカル CLI は Bucket を無視し、`--db` > DB 環境変数 > `outputs/local-league.sqlite3` を使います。クラウドの認証にはサービスアカウントを使い、キー JSON をリポジトリやフロントに置きません。

## 構築と検証

実際にリソースを作成・更新する手順は[リーグ構築](25-league-deployment.md)に一本化します。単に Service だけをデプロイしても定期集計と永続化は完成しません。今回の整理段階では構築スクリプトを実行していません。

次段階で最終 Git SHA、イメージ digest、Service revision、Job のイメージ、Scheduler 設定、Bucket/IAM、実行時刻を記録します。公開 GET の成功だけでは自動集計や再起動後の保存を検証したことになりません。

## 提出と凍結

公式締切は **2026-11-10 19:00 JST**。GitHub Push とフォーム送信を期限前に完了します。以降 **2026-11-14 終了まで**デプロイ URL を稼働させ、コード・Prompt・モデル・機能設定を変更しません。再デプロイ、バグ修正、手動再起動、認証更新による復旧は禁止です。通常の自動スケール・定期処理・審査操作によるデータ更新、クレジット補充は公式ルールの範囲で認められます。

期限前に課金・クレジット、権限、定期処理、保存、公開アクセスを確認します。予算通知や最大インスタンス数は課金上限保証ではありません。公式提出先では Actions と Pages を利用できないため、開発側で検証します。

[公式ルール](https://docs.google.com/document/d/1r2QRvMQbcJqhmYAEKAFTN9Co_zsJzvFhxfuS1wx1FJE/edit) / [Cloud Run コンテナー契約](https://docs.cloud.google.com/run/docs/container-contract)

## ローカル HTTP の確認

```bash
python -m reliefroute.server --db outputs/check.sqlite3 --port 8002
# 別ターミナル。既存のローカルサーバーに対して実行
python scripts/smoke.py http://127.0.0.1:8002
```

`smoke.py` は健康状態、固定静的資源、模擬試合と比較を確認します。リーグの定期実行や保存を証明するものではありません。ブラウザーでは戦略変更、試合実行、タイムライン移動、比較結果からの再生、JSON 保存、三言語と狭い画面を別途確認します。

本番の Gunicorn 設定・Dockerfile は保持していますが、本輪ではコンテナー構築やクラウド操作を実施していません。旧資料の 512 MiB / 30 秒という初期デプロイ例は現行の設定と異なるため復元していません。最終イメージの構築と Service/Job の更新は、費用と実設定を確認する段階で実行します。
