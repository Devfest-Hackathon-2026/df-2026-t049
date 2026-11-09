# 第三者依存・素材・ライセンス確認

## 確認範囲

2026-11-09、基準 `8974761` のコードと依存宣言、および第一段階の登録メタデータ確認をもとに整理しました。最終コンテナーの全 OS パッケージ・推移的依存関係の一覧と脆弱性検査は次段階で取得します。本表は公式の著作物利用シートに転記するための根拠であり、指定様式への記入の代わりではありません。

| 対象 | 使用箇所・出所 | ライセンス・対応 |
| --- | --- | --- |
| Python 3.13 / 標準ライブラリ | エンジン、API、CLI、コンテナー | PSF License 等。実際の配布物の表示を保持 |
| Gunicorn 26.2.0 | Linux WSGI、[PyPI](https://pypi.org/project/gunicorn/26.2.0/) | MIT。配布物の著作権・許諾表示を保持 |
| google-cloud-storage 3.17.1 | 私有スナップショット、[PyPI](https://pypi.org/project/google-cloud-storage/3.17.1/) | Apache-2.0。LICENSE と該当する NOTICE 等を保持 |
| Cloud Storage の推移的依存関係 | google-auth、google-api-core、google-cloud-core、google-resumable-media、requests、google-crc32c 等 | 最終イメージで正確なバージョン・各 LICENSE/NOTICE を確認。全体を MIT と扱わない |
| python:3.13-slim | Python / Debian ベースイメージ | 構成部品ごとの許諾。最終 digest と OS パッケージ一覧を別途記録 |
| HTML/CSS/JS/SVG | リポジトリ内の地図・車両・UI | 外部画像・タイル・アイコン・フォント・音声の配信依存はコード上見当たらない。チームが権利関係を最終確認 |
| システムフォント | 利用者の端末にあるフォント | フォントファイルを同梱していない |
| 道路・需要・イベント | scenario.py / events.py の架空データ | 実災害個人データ・外部地図データを使わない |
| GitHub Actions | checkout / setup-python / setup-node | 各 action の許諾を維持。開発 CI 用で、公式提出先では実行不可 |
| 動画の追加素材 | 別担当の最終 MP4 | 音楽・画像・音声等を追加する場合は出所と利用条件を別途確認 |

Google Maps、Gemini、Vertex AI、Firebase SDK、外部データセットは製品に接続していません。クラウドのサービス利用条件は OSS のライセンスとは別です。開発支援ツールの使用はコードを自動的にパブリックドメインにするものではありません。公式の AI 利用必須欄は[提出原稿](19-submission-draft-ja.md)をもとに第五段階で確認します。

## プロジェクトの許諾と公式 MIT

チームの決定に基づき、プロジェクト固有のコードとドキュメントに公式提出先の [MIT License](../LICENSE) を採用しました。全文と `Copyright (c) 2026 The contributors of this repository` の表示を保持しています。

第三者の依存・素材には各配布物のライセンスが独立して適用されます。直接依存の MIT / Apache-2.0 との明白な衝突は見つかっていませんが、全推移的依存・OS パッケージの確認は最終イメージで行います。既存の LICENSE / NOTICE を削除したり、第三者の資産を MIT に再許諾したりしません。

## 公開前の確認

- 第三者素材と追加動画素材の出所・利用条件の最終確認。
- 最終イメージの `python -m pip freeze` と各配布物の LICENSE/NOTICE、OS パッケージ情報を取得。
- 依存の脆弱性を最終解決バージョンで確認。第一段階の直接依存 OSV 照会のみで全イメージの安全を断定しない。
- 公式利用シートに実際の素材と依存を記入し、例示行を削除。
- 秘密情報・DB・トークン・ログを公開しない。履歴をそのまま公開せず、最終ファイルスナップショットを確認。
