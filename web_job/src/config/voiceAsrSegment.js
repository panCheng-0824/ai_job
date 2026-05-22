/**
 * 语音输入分段 ASR：在沿用现有 /api/voice/transcribe 的前提下，
 * 通过「最长单段 + 静音切段」控制单次上传体量；可选「长静音自动发送」。
 * 修改本文件后保存即可生效（无需后端改动）。
 */
export const VOICE_ASR_SEGMENT = {
  /** 单段录音最长毫秒，超时强制停止本段并识别（防止一路攒太长） */
  maxSegmentMs: 5000,

  /** 本段内已有说话声后，连续静音达到该毫秒则截断本段并识别 */
  silenceCutMs: 1000,

  /** 自上一次检测到说话声起，连续静音达到该毫秒视为说完了：结束录音并触发 onAutoSend */
  silenceSendMs: 5000,

  /**
   * 时域 RMS 判定为「有声」的下限（约 0～0.3）。环境噪大时可略调高；过于迟钝则略调低。
   */
  silenceRmsThreshold: 0.014,

  /** 单段录音短于该毫秒则跳过 ASR（噪声/空段），手动停止时的最后一段不受此限 */
  minSegmentMs: 400,

  /** 单段 Blob 小于该字节则跳过 ASR（同上） */
  minSegmentBytes: 1800,

  /** 两次 ASR 请求之间的最短间隔毫秒，减轻服务端压力 */
  minAsrIntervalMs: 350,

  /** 是否在长静音时调用 onAutoSend（关闭则仅分段填入输入框，需用户手动点发送） */
  autoSendOnSilence: true,

  /**
   * 为 true：自动发送后不关麦，继续聆听下一轮（仅手动点按钮结束录音）。
   * 为 false：每次自动发送后结束本轮录音。
   */
  continuousListening: true
};
