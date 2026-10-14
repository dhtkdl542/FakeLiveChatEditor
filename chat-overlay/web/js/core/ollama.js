// Ollama 추천 모델과, 서버 상태를 화면에 보여줄 형태로 바꾸는 뷰모델
import { fmtBytes } from "./format.js";

export const OLLAMA_BASE = "http://127.0.0.1:11434/v1";

export const MODEL_CATALOG = Object.freeze([
  { name: "huihui_ai/exaone3.5-abliterated:7.8b", size: "4.8GB", uncensored: true, recommended: true,
    title: "EXAONE 3.5 7.8B", note: "LG가 만든 한국어 특화 모델의 검열 해제판. 한국어 채팅 말투가 가장 자연스럽습니다. VRAM 6GB 이상." },
  { name: "huihui_ai/exaone3.5-abliterated:2.4b", size: "1.6GB", uncensored: true, recommended: false,
    title: "EXAONE 3.5 2.4B", note: "위 모델의 경량판. 저사양 PC나 VRAM 4GB 이하에서도 돌아갑니다. 말투는 조금 단조롭습니다." },
  { name: "huihui_ai/gemma-4-abliterated:12b", size: "7.6GB", uncensored: true, recommended: false,
    title: "Gemma 4 12B", note: "구글 Gemma 4의 검열 해제판. 드립이 다양합니다. VRAM 10GB 이상. 최신 Ollama가 필요하니 오류가 나면 [Ollama 업데이트]를 누르세요." },
  { name: "huihui_ai/qwen3.5-abliterated:9b", size: "6.6GB", uncensored: true, recommended: false,
    title: "Qwen 3.5 9B", note: "알리바바 Qwen 3.5의 검열 해제판. 답하기 전에 생각하는 단계가 있어서 느릴 수 있습니다. 최신 Ollama가 필요합니다." },
  { name: "dolphin3:8b", size: "4.9GB", uncensored: true, recommended: false,
    title: "Dolphin 3 8B (Ollama 공식)", note: "Ollama 공식 라이브러리의 검열 해제 모델. 영어 위주라 한국어가 어색합니다." },
].map(Object.freeze));

const isEmbedding = name => /embed/i.test(name);

export class OllamaViewModel {
  static from(status, catalog = MODEL_CATALOG) {
    const { installed, running, version, models, job } = status;
    const busy = job.status === "running";
    const have = new Set(models.map(m => m.name));

    let statusText, statusKind;
    if (running) {
      statusText = `Ollama 실행 중 (v${version}) · 설치된 모델 ${models.length}개`;
      statusKind = "ok";
    } else if (installed) {
      statusText = "Ollama가 꺼져 있습니다. 대사를 만들 때 창 없이 백그라운드에서 자동으로 켜집니다.";
      statusKind = "";
    } else {
      statusText = "Ollama가 설치돼 있지 않습니다. [Ollama 설치]를 누르면 ollama.com에서 공식 설치 파일을 받아 설치합니다.";
      statusKind = "warn";
    }

    const percent = job.total ? Math.round((100 * job.completed) / job.total)
      : job.status === "done" ? 100 : busy ? 3 : 0;

    return {
      statusText, statusKind, busy, running,
      installLabel: installed ? "Ollama 업데이트" : "Ollama 설치",
      showStart: installed && !running,
      job: {
        visible: job.status !== "idle",
        text: job.message + (job.total ? ` (${fmtBytes(job.completed)} / ${fmtBytes(job.total)})` : ""),
        percent,
        cancellable: busy && job.kind !== "start",
        kind: job.status === "error" ? "warn" : job.status === "done" ? "ok" : "",
      },
      catalog: catalog.map(m => ({ ...m, installed: have.has(m.name) })),
      installed: models.map(m => ({ name: m.name, size: m.size, sizeText: fmtBytes(m.size), usable: !isEmbedding(m.name) })),
      usableModels: models.map(m => m.name).filter(n => !isEmbedding(n)),
    };
  }
}
