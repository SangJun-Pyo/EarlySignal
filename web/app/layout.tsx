import type { Metadata } from "next";
import "@fontsource/ibm-plex-sans-kr/400.css";
import "@fontsource/ibm-plex-sans-kr/500.css";
import "@fontsource/ibm-plex-sans-kr/600.css";
import "@fontsource/ibm-plex-mono/400.css";
import "./globals.css";
export const metadata: Metadata = {
  title: "EarlySignal · 고객의 목소리를, 조사의 근거로.",
  description:
    "NHTSA 공개 신고 파일을 AI로 분류하고, 통계 경보의 원문을 검토해 조사 요청서를 완성합니다. 접수일 기준 과거 재현입니다.",
};
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
