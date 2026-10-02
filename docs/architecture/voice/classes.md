# Diagramme de classes - Voix

```mermaid
classDiagram
%% source: app/voice
class AcousticConfig {
  +TTS_COMMAND
  +GROQ_STT_URL
}
class ZeroRAMAudioRecorder {
  +record_seconds(duration)
}
class GroqWhisperSTT {
  +transcribe(audio_buffer)
}
class LinuxNativeTTS {
  +speak(text)
}
class AcousticZeroRAMFacade {
  +tts
  +stt
  +speak(text)
  +listen_and_transcribe()
}
class LiveHologramSession {
  +session_id
  +status
  +audio_in_buffer
  +ingest_audio_chunk(chunk)
  +handle_barge_in()
  +close()
}
class RealtimeCallGateway {
  +sessions
  +create_session(user)
  +dispatch_stealth_action(session_id, instruction)
  +get_mini_app_html(session_id)
}
AcousticZeroRAMFacade o-- LinuxNativeTTS
AcousticZeroRAMFacade o-- GroqWhisperSTT
RealtimeCallGateway o-- LiveHologramSession
```
