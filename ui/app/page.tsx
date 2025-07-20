"use client"

import { useState, useEffect, useRef } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Loader2, ChevronDown, ChevronUp, AlertCircle, CheckCircle } from "lucide-react"
import { Alert, AlertDescription } from "@/components/ui/alert"

type TestPhase = "setup" | "generating" | "testing" | "complete" | "error"

interface Persona {
  name: string
  system_prompt: string
}

interface LogMessage {
  timestamp: string
  session_id: string
  persona_name?: string
  type: string
  message: string
  data?: any
}

const API_BASE_URL = "http://localhost:8000"

export default function PersonaFlowApp() {
  const [phase, setPhase] = useState<TestPhase>("setup")
  const [apiUrl, setApiUrl] = useState("https://persona-flow-mock-api-1005425382429.europe-west4.run.app/")
  const [testGoal, setTestGoal] = useState(
    "Find and buy a wireless mouse"
  )
  const [targetAudience, setTargetAudience] = useState("budget-conscious online shoppers")
  const [numPersonas, setNumPersonas] = useState(3)
  const [personas, setPersonas] = useState<Persona[]>([])
  const [logs, setLogs] = useState<LogMessage[]>([])
  const [showLogs, setShowLogs] = useState(true)
  const [sessionId, setSessionId] = useState<string>("")
  const [error, setError] = useState<string>("")
  const [finalReport, setFinalReport] = useState<string>("")

  // WebSocket for real-time logs
  const [websocket, setWebsocket] = useState<WebSocket | null>(null)
  const logContainerRef = useRef<HTMLDivElement>(null)

  const connectWebSocket = (sessionId: string) => {
    const ws = new WebSocket(`ws://localhost:8000/api/test-sessions/${sessionId}/logs`)
    
    ws.onopen = () => {
      console.log("WebSocket connected for session:", sessionId)
    }
    
    ws.onmessage = (event) => {
      try {
        const logMessage: LogMessage = JSON.parse(event.data)
        setLogs(prev => [...prev, logMessage])
        
        // Auto-scroll to bottom after a short delay to allow rendering
        setTimeout(() => {
          if (logContainerRef.current) {
            logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight
          }
        }, 100)
        
        // Check for completion
        if (logMessage.type === "complete" && logMessage.data?.report) {
          setFinalReport(logMessage.data.report)
          setPhase("complete")
        }
      } catch (error) {
        console.error("Error parsing WebSocket message:", error)
      }
    }
    
    ws.onclose = () => {
      console.log("WebSocket disconnected")
    }
    
    ws.onerror = (error) => {
      console.error("WebSocket error:", error)
    }
    
    setWebsocket(ws)
  }

  const disconnectWebSocket = () => {
    if (websocket) {
      websocket.close()
      setWebsocket(null)
    }
  }

  useEffect(() => {
    return () => {
      disconnectWebSocket()
    }
  }, [])

  const generatePersonas = async () => {
    if (!targetAudience.trim()) {
      setError("Please enter a target audience description")
      return null
    }

    try {
      setPhase("generating")
      setError("")
      
      const response = await fetch(`${API_BASE_URL}/api/generate-personas`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          market_segment: targetAudience,
          num_personas: numPersonas
        })
      })

      if (!response.ok) {
        throw new Error(`Failed to generate personas: ${response.statusText}`)
      }

      const data = await response.json()
      setPersonas(data.personas)
      return data.personas
    } catch (error) {
      console.error("Error generating personas:", error)
      setError(error instanceof Error ? error.message : "Failed to generate personas")
      setPhase("error")
      return null
    }
  }

  const runTests = async (personasToUse?: Persona[]) => {
    if (!apiUrl.trim()) {
      setError("Please enter a target API URL")
      return
    }

    // Use provided personas or fall back to state
    const actualPersonas = personasToUse || personas
    
    if (!actualPersonas || actualPersonas.length === 0) {
      setError("No personas available to test")
      return
    }

    try {
      setPhase("testing")
      setLogs([])
      setError("")

      console.log(" Sending personas to backend:", actualPersonas.length)

      // First, create the session but don't start tests yet
      const response = await fetch(`${API_BASE_URL}/api/run-tests`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          personas: actualPersonas,
          test_goal: testGoal,
          api_url: apiUrl,
          max_steps: 8
        })
      })

      if (!response.ok) {
        throw new Error(`Failed to start tests: ${response.statusText}`)
      }

      const data = await response.json()
      setSessionId(data.session_id)
      
      // Connect WebSocket immediately for real-time logs
      console.log("🔌 Connecting WebSocket for session:", data.session_id)
      connectWebSocket(data.session_id)
      
    } catch (error) {
      console.error("Error running tests:", error)
      setError(error instanceof Error ? error.message : "Failed to run tests")
      setPhase("error")
    }
  }

  const handleRunTests = async () => {
    // First generate personas, then run tests
    const generatedPersonas = await generatePersonas()
    if (generatedPersonas && generatedPersonas.length > 0) {
      // Pass the personas directly to runTests to avoid state timing issues
      console.log("Generated personas, now running tests with:", generatedPersonas.length)
      await runTests(generatedPersonas)
    }
  }

  const resetDemo = () => {
    setPhase("setup")
    setPersonas([])
    setLogs([])
    setSessionId("")
    setError("")
    setFinalReport("")
    disconnectWebSocket()
  }

  const parseMarkdownLine = (text: string) => {
    // Handle inline bold text (**text**)
    const boldRegex = /\*\*(.*?)\*\*/g
    const parts = []
    let lastIndex = 0
    let match
    
    while ((match = boldRegex.exec(text)) !== null) {
      // Add text before the bold part
      if (match.index > lastIndex) {
        parts.push(text.slice(lastIndex, match.index))
      }
      // Add the bold part
      parts.push(<strong key={match.index} className="font-semibold text-slate-800">{match[1]}</strong>)
      lastIndex = match.index + match[0].length
    }
    
    // Add remaining text
    if (lastIndex < text.length) {
      parts.push(text.slice(lastIndex))
    }
    
    return parts.length > 0 ? parts : text
  }

  const formatLogMessage = (log: LogMessage, index: number) => {
    const timestamp = new Date(log.timestamp).toLocaleTimeString()
    const prefix = log.persona_name ? `[${log.persona_name}]` : ""
    
    let icon = "ℹ️"
    let bgColor = "bg-slate-50"
    let textColor = "text-slate-700"
    let borderColor = "border-slate-200"
    
    switch (log.type) {
      case "thinking":
        icon = "🤔"
        bgColor = "bg-blue-50"
        textColor = "text-blue-800"
        borderColor = "border-blue-200"
        break
      case "acting":
        icon = "🛠️"
        bgColor = "bg-amber-50"
        textColor = "text-amber-800"
        borderColor = "border-amber-200"
        break
      case "observing":
        icon = "👀"
        bgColor = "bg-green-50"
        textColor = "text-green-800"
        borderColor = "border-green-200"
        break
      case "error":
        icon = "❌"
        bgColor = "bg-red-50"
        textColor = "text-red-800"
        borderColor = "border-red-200"
        break
      case "complete":
        icon = "✅"
        bgColor = "bg-emerald-50"
        textColor = "text-emerald-800"
        borderColor = "border-emerald-200"
        break
    }
    
    return (
      <div 
        key={index} 
        className={`mb-2 p-2 rounded-lg border ${bgColor} ${borderColor} ${textColor} transition-all duration-300 ease-in-out animate-in slide-in-from-right-2`}
      >
        <div className="flex items-start gap-2">
          <span className="text-base flex-shrink-0">{icon}</span>
          <div className="flex-1 font-mono text-xs">
            <span className="text-slate-500">{timestamp}</span>
            {prefix && <span className="text-purple-600 font-semibold ml-2">{prefix}</span>}
            <div className="mt-1 leading-relaxed">{log.message}</div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50">
      <div className="mx-auto max-w-4xl px-6 py-12">
        {/* Header */}
        <div className="text-center mb-16">
          <h1 className="text-5xl font-bold bg-gradient-to-r from-blue-600 via-purple-600 to-indigo-600 bg-clip-text text-transparent mb-4">
            PersonaFlow
          </h1>
          <p className="text-xl text-slate-600 font-medium">Agentic User testing for your product</p>
          <div className="mt-4 flex justify-center gap-2">
            <Badge variant="outline" className="text-green-700 border-green-200 bg-green-50">
              <CheckCircle className="w-3 h-3 mr-1" />
              Backend Connected
            </Badge>
            <Badge variant="outline" className="text-blue-700 border-blue-200 bg-blue-50">
              Live Integration
            </Badge>
          </div>
        </div>

        {/* Error Alert */}
        {error && (
          <Alert className="mb-6 border-red-200 bg-red-50">
            <AlertCircle className="h-4 w-4 text-red-600" />
            <AlertDescription className="text-red-800">
              {error}
            </AlertDescription>
          </Alert>
        )}

        <div className="space-y-8">
          {/* Setup Card */}
          <Card className="border-0 shadow-lg bg-white/80 backdrop-blur-sm">
            <CardHeader className="pb-6">
              <CardTitle className="text-2xl font-semibold text-slate-800 flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-gradient-to-r from-blue-500 to-indigo-500 flex items-center justify-center text-white font-bold text-sm">
                  1
                </div>
                Test Configuration
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-3">
                <Label htmlFor="api-url" className="text-slate-700 font-medium">
                  Target API URL
                </Label>
                <Input
                  id="api-url"
                  placeholder="e.g., https://api.myapp.com"
                  value={apiUrl}
                  onChange={(e) => setApiUrl(e.target.value)}
                  className="border-slate-200 focus:border-blue-400 focus:ring-blue-400/20"
                  disabled={phase !== "setup"}
                />
              </div>

              <div className="space-y-3">
                <Label htmlFor="test-goal" className="text-slate-700 font-medium">
                  Test Goal
                </Label>
                <Textarea
                  id="test-goal"
                  rows={3}
                  value={testGoal}
                  onChange={(e) => setTestGoal(e.target.value)}
                  className="border-slate-200 focus:border-blue-400 focus:ring-blue-400/20 resize-none"
                  disabled={phase !== "setup"}
                />
              </div>

              <div className="space-y-3">
                <Label htmlFor="target-audience" className="text-slate-700 font-medium">
                  Target Audience Description
                </Label>
                <Textarea
                  id="target-audience"
                  rows={4}
                  placeholder="e.g., Tech-savvy university students who are impatient and care about API efficiency, but are also on a tight budget."
                  value={targetAudience}
                  onChange={(e) => setTargetAudience(e.target.value)}
                  className="border-slate-200 focus:border-blue-400 focus:ring-blue-400/20 resize-none"
                  disabled={phase !== "setup"}
                />
              </div>

              <div className="space-y-3">
                <Label htmlFor="num-personas" className="text-slate-700 font-medium">
                  Number of Personas to Generate
                </Label>
                <Input
                  id="num-personas"
                  type="number"
                  min="1"
                  max="6"
                  value={numPersonas}
                  onChange={(e) => setNumPersonas(Math.max(1, Math.min(6, parseInt(e.target.value) || 1)))}
                  className="border-slate-200 focus:border-blue-400 focus:ring-blue-400/20"
                  disabled={phase !== "setup"}
                />
              </div>

              <div className="flex gap-3">
                <Button
                  onClick={handleRunTests}
                  className="flex-1 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-medium py-3 rounded-lg transition-all duration-200 shadow-lg hover:shadow-xl"
                  disabled={phase !== "setup" && phase !== "error"}
                >
                  {phase === "setup" || phase === "error" ? (
                    "Generate Personas & Run Tests"
                  ) : phase === "generating" ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Generating Personas...
                    </>
                  ) : phase === "testing" ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Running Tests...
                    </>
                  ) : (
                    <>
                      <CheckCircle className="w-4 h-4 mr-2" />
                      Tests Complete
                    </>
                  )}
                </Button>
                
                {phase !== "setup" && (
                  <Button
                    onClick={resetDemo}
                    variant="outline"
                    className="border-slate-200 hover:border-slate-300"
                  >
                    Reset
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Live Progress Card */}
          {phase !== "setup" && phase !== "error" && (
            <Card className="border-0 shadow-lg bg-white/80 backdrop-blur-sm">
              <CardHeader className="pb-6">
                <CardTitle className="text-2xl font-semibold text-slate-800 flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-gradient-to-r from-emerald-500 to-teal-500 flex items-center justify-center text-white font-bold text-sm">
                    2
                  </div>
                  Live Test Progress
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                {phase === "generating" && (
                  <div className="flex items-center justify-center py-12">
                    <div className="text-center space-y-4">
                      <Loader2 className="h-8 w-8 animate-spin mx-auto text-blue-600" />
                      <p className="text-lg text-slate-600 font-medium">Architect agent is generating personas via Vertex AI...</p>
                    </div>
                  </div>
                )}

                {(phase === "testing" || phase === "complete") && personas.length > 0 && (
                  <>
                    <div className="space-y-4">
                      <h3 className="text-lg font-semibold text-slate-800">Generated Personas:</h3>
                      <div className="flex flex-wrap gap-3">
                        {personas.map((persona, index) => (
                          <Badge
                            key={index}
                            variant="secondary"
                            className="text-sm py-2 px-4 bg-gradient-to-r from-purple-100 to-pink-100 text-purple-700 border-purple-200 font-medium"
                          >
                            {persona.name}
                          </Badge>
                        ))}
                      </div>
                    </div>

                    <div className="space-y-4">
                      <div className="flex items-center justify-between">
                        <h3 className="text-lg font-semibold text-slate-800">
                          Agent Logs: 
                          <span className="text-sm font-normal text-slate-600 ml-2">
                            ({logs.length} messages)
                          </span>
                        </h3>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setShowLogs(!showLogs)}
                          className="flex items-center gap-2 text-slate-600 hover:text-slate-800 border-slate-200 hover:border-slate-300"
                        >
                          {showLogs ? (
                            <>
                              <ChevronUp className="h-4 w-4" />
                              Hide Logs
                            </>
                          ) : (
                            <>
                              <ChevronDown className="h-4 w-4" />
                              Show Logs
                            </>
                          )}
                        </Button>
                      </div>
                      {showLogs && (
                        <div 
                          ref={logContainerRef}
                          className="bg-gradient-to-br from-slate-50 to-slate-100 p-4 rounded-xl border border-slate-200 max-h-96 overflow-y-auto scroll-smooth"
                        >
                          {logs.length > 0 ? (
                            <div className="space-y-1">
                              {logs.map((log, index) => formatLogMessage(log, index))}
                            </div>
                          ) : (
                            phase === "testing" && (
                              <div className="text-slate-500 italic text-center py-8">
                                <div className="animate-pulse">Waiting for test logs...</div>
                              </div>
                            )
                          )}
                        </div>
                      )}
                    </div>
                  </>
                )}
              </CardContent>
            </Card>
          )}

          {/* Final Report Card */}
          {phase === "complete" && finalReport && (
            <Card className="border-0 shadow-lg bg-white/80 backdrop-blur-sm">
              <CardHeader className="pb-6">
                <CardTitle className="text-2xl font-semibold text-slate-800 flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-gradient-to-r from-amber-500 to-orange-500 flex items-center justify-center text-white font-bold text-sm">
                    3
                  </div>
                  Final Report
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="prose prose-slate max-w-none">
                  <div className="leading-relaxed space-y-2">
                    {finalReport.split("\n").map((line, index) => {
                      const trimmedLine = line.trim()
                      
                      if (line.startsWith("### ")) {
                        return (
                          <h3 key={index} className="text-2xl font-bold mt-8 mb-4 text-slate-800">
                            {parseMarkdownLine(line.replace("### ", ""))}
                          </h3>
                        )
                      } else if (line.startsWith("#### ")) {
                        return (
                          <h4 key={index} className="text-xl font-semibold mt-6 mb-3 text-slate-700">
                            {parseMarkdownLine(line.replace("#### ", ""))}
                          </h4>
                        )
                      } else if (line.startsWith("**") && line.endsWith("**") && !line.includes(" ")) {
                        // Full-line bold (section headers)
                        return (
                          <p key={index} className="font-semibold text-slate-800 mb-2 text-lg">
                            {line.replace(/\*\*/g, "")}
                          </p>
                        )
                      } else if (line.startsWith("- ")) {
                        return (
                          <div key={index} className="flex items-start ml-6 mb-2">
                            <span className="text-slate-400 mr-2">•</span>
                            <span className="text-slate-600">
                              {parseMarkdownLine(line.replace("- ", ""))}
                            </span>
                          </div>
                        )
                      } else if (/^\d+\./.test(trimmedLine)) {
                        // Numbered lists
                        return (
                          <div key={index} className="flex items-start ml-6 mb-2">
                            <span className="text-slate-600 mr-2 font-medium">
                              {trimmedLine.match(/^\d+\./)?.[0]}
                            </span>
                            <span className="text-slate-600">
                              {parseMarkdownLine(trimmedLine.replace(/^\d+\.\s*/, ""))}
                            </span>
                          </div>
                        )
                      } else if (line === "---") {
                        return <hr key={index} className="my-8 border-slate-300" />
                      } else if (trimmedLine === "") {
                        return <div key={index} className="h-3" />
                      } else {
                        return (
                          <p key={index} className="mb-3 text-slate-600 leading-relaxed">
                            {parseMarkdownLine(line)}
                          </p>
                        )
                      }
                    })}
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}