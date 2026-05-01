package com.homeworkgrader.storage;

import java.io.IOException;
import java.io.OutputStream;

final class OutputStreamSink extends OutputStream {
    static final OutputStreamSink INSTANCE = new OutputStreamSink();

    private OutputStreamSink() {
    }

    @Override
    public void write(int b) throws IOException {
        // Intentionally discard bytes while DigestInputStream updates the hash.
    }
}
