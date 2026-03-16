import { useState } from 'react';
import { Play, Plus, Server, GitBranch, Settings, History } from 'lucide-react';
import LiveFeed from './components/LiveFeed';

function App() {
  const [activeTab, setActiveTab] = useState('new-run');
  const [repoPath, setRepoPath] = useState('');
  const [request, setRequest] = useState('');
  const [isRunning, setIsRunning] = useState(false);

  const startRun = () => {
    if (!repoPath || !request) return;
    setIsRunning(true);
  };

  return (
    <div className="flex h-screen bg-background text-foreground dark">
      {/* Sidebar */}
      <div className="w-64 border-r border-border bg-card flex flex-col">
        <div className="p-4 border-b border-border">
          <h1 className="text-xl font-bold flex items-center gap-2">
            <Server className="w-6 h-6 text-primary" />
            Maestro UI
          </h1>
        </div>
        
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          <div>
            <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Projects</h2>
            <div className="space-y-1">
              {/* Placeholder for project list */}
              <button className="w-full text-left px-3 py-2 text-sm rounded-md bg-accent text-accent-foreground flex items-center gap-2">
                <GitBranch className="w-4 h-4" />
                Current Workspace
              </button>
              <button className="w-full text-left px-3 py-2 text-sm rounded-md text-muted-foreground hover:bg-muted flex items-center gap-2">
                <Plus className="w-4 h-4" />
                Add Project
              </button>
            </div>
          </div>

          <div>
            <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Actions</h2>
            <div className="space-y-1">
              <button 
                onClick={() => setActiveTab('new-run')}
                className={`w-full text-left px-3 py-2 text-sm rounded-md flex items-center gap-2 ${activeTab === 'new-run' ? 'bg-accent text-accent-foreground' : 'text-muted-foreground hover:bg-muted'}`}
              >
                <Play className="w-4 h-4" />
                New Run
              </button>
              <button 
                onClick={() => setActiveTab('history')}
                className={`w-full text-left px-3 py-2 text-sm rounded-md flex items-center gap-2 ${activeTab === 'history' ? 'bg-accent text-accent-foreground' : 'text-muted-foreground hover:bg-muted'}`}
              >
                <History className="w-4 h-4" />
                History
              </button>
              <button 
                onClick={() => setActiveTab('settings')}
                className={`w-full text-left px-3 py-2 text-sm rounded-md flex items-center gap-2 ${activeTab === 'settings' ? 'bg-accent text-accent-foreground' : 'text-muted-foreground hover:bg-muted'}`}
              >
                <Settings className="w-4 h-4" />
                Settings
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <div className="flex-1 p-6 overflow-y-auto">
          {activeTab === 'new-run' && (
            <div className="max-w-4xl mx-auto space-y-6 h-full flex flex-col">
              <div>
                <h2 className="text-2xl font-bold tracking-tight">Initiate Maestro Run</h2>
                <p className="text-muted-foreground">Provide a repository path and describe the feature or fix you want to implement.</p>
              </div>

              {!isRunning ? (
                <div className="space-y-4 bg-card p-6 rounded-lg border border-border">
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Repository Path</label>
                    <input 
                      type="text" 
                      value={repoPath}
                      onChange={(e) => setRepoPath(e.target.value)}
                      placeholder="/home/user/projects/my-app"
                      className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Request</label>
                    <textarea 
                      value={request}
                      onChange={(e) => setRequest(e.target.value)}
                      placeholder="e.g. Implement a new authentication middleware..."
                      rows={5}
                      className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary resize-none"
                    />
                  </div>
                  <button 
                    onClick={startRun}
                    className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-md transition-colors flex justify-center items-center gap-2"
                  >
                    <Play className="w-4 h-4" />
                    Start AI Pipeline
                  </button>
                </div>
              ) : (
                <div className="flex-1 flex flex-col min-h-0 space-y-4">
                  <div className="flex justify-between items-center">
                    <h3 className="text-lg font-medium flex items-center gap-2">
                      <span className="relative flex h-3 w-3">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-3 w-3 bg-green-500"></span>
                      </span>
                      Pipeline Active
                    </h3>
                    <div className="flex gap-2">
                      <button 
                        onClick={() => setIsRunning(false)}
                        className="text-sm px-3 py-1 bg-destructive text-destructive-foreground hover:bg-red-700 rounded-md"
                      >
                        Abort Run
                      </button>
                    </div>
                  </div>
                  <div className="flex-1 min-h-0">
                     <LiveFeed 
                        repoPath={repoPath} 
                        request={request} 
                        onFinished={(code) => console.log('Run finished with code', code)} 
                     />
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === 'history' && (
            <div className="flex items-center justify-center h-full text-muted-foreground">
              History view is under construction.
            </div>
          )}
          
          {activeTab === 'settings' && (
            <div className="flex items-center justify-center h-full text-muted-foreground">
              Settings view is under construction.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;