# CHAEWON ARCHIVE

tripleS S21 김채원 팬 아카이브 · CREATED BY @bbangshion

React + TypeScript + Vite 기반. 기존 SHION/YEONJI ARCHIVE의 UI 구조에서 독립된 별도 저장소입니다.

## 빠른 시작

1. `chaewon-archive`라는 **새 저장소**를 만들고 이 ZIP의 `chaewon-archive/` 폴더 안 파일을 저장소 최상단에 업로드합니다. 다른 멤버의 기존 저장소를 덮어쓰지 마세요.
2. Settings → Pages → Source → GitHub Actions
3. Actions → Deploy CHAEWON ARCHIVE 실행. 빌드 성공 뒤 `https://bbangshion.github.io/chaewon-archive/` 주소 확인
4. 필요 시 Actions → Import CHAEWON S21 Objekts from WAV ARCHIVE 실행. WAV 저장소 구조 변경 시 동기화는 실패할 수 있고 기존 데이터는 유지됩니다.

사진과 영상은 검증된 항목만 포함. 현재 확인된 초기 데이터는 제공 사진 1장, 공식 YouTube 5개이며 S21 오브젝트는 동기화 대기 상태입니다.

프로필: `public/data/chaewon.json`  · 사진: `public/data/photos.json` · 영상: `public/data/films.json` · 오브젝트: `public/data/objekt.json` · 기록: `public/data/chaewon-activities.json`

종합 전시관은 `/gallery/`에 설치되어 있으며 동일한 `photos.json`을 표시합니다. PHOTO 메뉴에서도 이동 가능.

### 주의
사용자가 제공한 사진은 원본 그대로 사이트에 포함됩니다. 실제 저작권자 허락 여부와 출처 표시는 별도 검수하세요. 부정확한 날짜를 임의 생성하거나, 다른 멤버 데이터를 병합하지 마세요. 기존 사진·영상 전체를 자동 복제한 상태는 아닙니다.

개발 환경: `npm install && npm run build` / `npm run dev`
