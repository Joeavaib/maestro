import { useEffect, useRef } from 'react';
import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import '@xterm/xterm/css/xterm.css';

interface LiveFeedProps {
  repoPath: string;
  request: string;
  onFinished?: (exitCode: number) => void;
}

export default function LiveFeed({ repoPath, request, onFinished }: LiveFeedProps) {
  const terminalRef = useRef<HTMLDivElement>(null);
  const xtermRef = useRef<Terminal | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (!terminalRef.current) return;

    // Initialize xterm.js
    const term = new Terminal({
      theme: {
        background: '#0a0a0a',
        foreground: '#f8f8f2',
      },
      fontFamily: 'Menlo, Monaco, "Courier New", monospace',
      fontSize: 14,
    });
    
    const fitAddon = new FitAddon();
    term.loadAddon(fitAddon);
    term.open(terminalRef.current);
    fitAddon.fit();
    xtermRef.current = term;

    term.writeln('\x1b[32m[System] Connecting to Maestro Core (SSE)...\x1b[0m');

    abortControllerRef.current = new AbortController();

    const startStream = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/run', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ repo_path: repoPath, request: request }),
          signal: abortControllerRef.current?.signal,
        });

        if (!response.ok || !response.body) {
          term.writeln(`\r\n\x1b[31m[Error] Failed to connect: ${response.statusText}\x1b[0m\r\n`);
          return;
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const parts = buffer.split('\n\n');
          buffer = parts.pop() || ''; // keep the last partial chunk

          for (const part of parts) {
            if (part.startsWith('data: ')) {
              try {
                const data = JSON.parse(part.slice(6));
                
                if (data.type === 'log') {
                  term.write(data.content.replace(/\n/g, '\r\n'));
                } else if (data.type === 'status') {
                  term.writeln(`\r\n\x1b[36m[Status] ${data.content}\x1b[0m\r\n`);
                  if (data.exit_code !== undefined && onFinished) {
                    onFinished(data.exit_code);
                  }
                } else if (data.type === 'error') {
                  term.writeln(`\r\n\x1b[31m[Error] ${data.content}\x1b[0m\r\n`);
                }
              } catch (e) {
                // Ignore parse errors from partial chunks or keep-alive pings
              }
            }
          }
        }
      } catch (err: any) {
        if (err.name !== 'AbortError') {
          term.writeln(`\r\n\x1b[31m[System] Connection error: ${err.message}\x1b[0m\r\n`);
        }
      } finally {
        term.writeln('\r\n\x1b[33m[System] Stream closed.\x1b[0m');
      }
    };

    startStream();

    const handleResize = () => fitAddon.fit();
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      if (abortControllerRef.current) {
        abortControllerRef.current.abort(); // Cancel the fetch request
      }
      term.dispose();
    };
  }, [repoPath, request]);

  return (
    <div className="w-full h-full bg-[#0a0a0a] rounded-lg overflow-hidden border border-border">
      <div className="bg-muted px-4 py-2 border-b border-border flex items-center">
        <div className="flex space-x-2">
          <div className="w-3 h-3 rounded-full bg-red-500"></div>
          <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
          <div className="w-3 h-3 rounded-full bg-green-500"></div>
        </div>
        <span className="ml-4 text-xs text-muted-foreground font-mono">Maestro Live Feed</span>
      </div>
      <div ref={terminalRef} className="h-[calc(100%-40px)] w-full p-2" />
    </div>
  );
}
