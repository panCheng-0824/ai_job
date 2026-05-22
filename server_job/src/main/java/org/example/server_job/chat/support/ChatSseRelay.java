package org.example.server_job.chat.support;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.util.function.Consumer;

/**
 * 将上游 SSE 文本流透传到客户端，并在收到 {@code event: done} 时回调完整 data JSON。
 */
public final class ChatSseRelay {

    private ChatSseRelay() {
    }

    public static void relay(InputStream in, OutputStream out, Consumer<String> onDonePayload) throws IOException {
        BufferedReader br = new BufferedReader(new InputStreamReader(in, StandardCharsets.UTF_8));
        String pendingEvent = null;
        StringBuilder dataAccum = new StringBuilder();
        String line;
        while ((line = br.readLine()) != null) {
            byte[] lineBytes = line.getBytes(StandardCharsets.UTF_8);
            out.write(lineBytes);
            out.write('\n');
            if (line.startsWith("event:")) {
                pendingEvent = line.substring(6).trim();
                dataAccum.setLength(0);
            } else if (line.startsWith("data:")) {
                if (dataAccum.length() > 0) {
                    dataAccum.append('\n');
                }
                dataAccum.append(line.substring(5).trim());
            } else if (line.isEmpty()) {
                if ("done".equals(pendingEvent) && dataAccum.length() > 0) {
                    onDonePayload.accept(dataAccum.toString());
                }
                pendingEvent = null;
                dataAccum.setLength(0);
            }
            out.flush();
        }
    }
}
