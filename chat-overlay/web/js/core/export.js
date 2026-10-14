// mp4 저장 요청 만들기
export function suggestOutputName(videoPath) {
  const file = videoPath.split(/[\\/]/).pop();
  const dot = file.lastIndexOf(".");
  return (dot > 0 ? file.slice(0, dot) : file) + "_chat.mp4";
}

/** previewMatchesVideo: 미리보기 타임라인(채팅 · 후원)이 실제 영상 길이로 만들어졌으면 그대로 보내서 결과를 똑같이 만든다.
 *  스티커는 시간과 상관없는 배치라 항상 보낸다. */
export function buildRenderRequest({ videoPath, outputPath, settings, events, previewMatchesVideo, stickers = [],
  donations = [] }) {
  const out = { ...settings, STICKERS: stickers };
  if (previewMatchesVideo) Object.assign(out, { EVENTS: events, DONATIONS: donations });
  return { videoPath, outputPath, settings: out };
}
