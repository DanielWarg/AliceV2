import { useState, useEffect } from "react";
import {
  GuardianStatusBanner,
  VoiceInterface,
  VoiceCommandInterface,
  AudioVisualizer,
  PerformanceHUD,
  useGuardian,
  useAliceAPI,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@alice/ui";
import type { AliceAPIConfig } from "@alice/api";

interface AliceHUDProps {
  config: AliceAPIConfig;
  className?: string;
}

export function AliceHUD({ config, className }: AliceHUDProps) {
  const [showPerformanceHUD, setShowPerformanceHUD] = useState(false);
  const [activeVoiceMode, setActiveVoiceMode] = useState<"interface" | "commands">("interface");
  const [isVoiceListening, setIsVoiceListening] = useState(false);
  const [isHealthy, setIsHealthy] = useState<boolean | null>(null);

  // Guardian system integration
  const {
    status: guardianStatus,
    shouldShowBanner,
    isDegraded,
    isEmergency,
  } = useGuardian({
    apiUrl: `${config.guardianURL}/health`,
    pollInterval: isDegraded ? 2000 : 5000, // Poll faster when degraded
  });

  // Alice API integration
  const {
    client,
    isConnected,
    isConnecting,
    error: apiError,
    connect,
    disconnect,
    sendMessage,
  } = useAliceAPI({
    config,
    autoConnect: true,
  });

  const handleVoiceCommand = async (command: string) => {
    try {
      if (!client) throw new Error("API client not available");

      const response = await client.sendChatMessage({ message: command });
      return response.response;
    } catch (error) {
      console.error("Voice command failed:", error);
      return "I apologize, but I encountered an error processing your request.";
    }
  };

  // Disable voice features in emergency mode
  const voiceFeaturesEnabled = !isEmergency && isConnected;

  return (
    <div
      className={`alice-hud min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 text-white ${className}`}
    >
      {/* Guardian Status Banner */}
      {shouldShowBanner && (
        <div className="fixed top-0 left-0 right-0 z-50 p-4">
          <GuardianStatusBanner status={guardianStatus} className="max-w-4xl mx-auto" />
        </div>
      )}

      {/* Main Container */}
      <div className={`container mx-auto p-6 space-y-8 ${shouldShowBanner ? "pt-24" : ""}`}>
        {/* Header */}
        <div className="text-center space-y-2">
          <h1 className="text-4xl font-bold bg-gradient-to-r from-cyan-400 to-blue-400 bg-clip-text text-transparent">
            Alice AI Assistant
          </h1>
          <div className="flex items-center justify-center space-x-4 text-sm">
            <span
              className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                isConnected
                  ? "bg-green-100 text-green-800"
                  : isConnecting
                    ? "bg-yellow-100 text-yellow-800"
                    : "bg-red-100 text-red-800"
              }`}
            >
              {isConnected ? "✓ Connected" : isConnecting ? "⟳ Connecting" : "✗ Disconnected"}
            </span>
            {guardianStatus && (
              <span
                className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                  guardianStatus.status === "normal"
                    ? "bg-green-100 text-green-800"
                    : "bg-yellow-100 text-yellow-800"
                }`}
              >
                Guardian: {guardianStatus.status}
              </span>
            )}
          </div>
        </div>

        {/* API Error Display */}
        {apiError && (
          <Card className="border-red-200 bg-red-50">
            <CardContent className="p-4">
              <div className="flex items-center space-x-2 text-red-800">
                <span>⚠️</span>
                <span className="font-medium">Connection Error: {apiError}</span>
                <Button size="sm" variant="outline" onClick={connect} disabled={isConnecting}>
                  Retry
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Voice Interface Section */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Voice Interface */}
          <Card className="bg-gray-800/50 border-gray-700">
            <CardHeader>
              <CardTitle className="text-cyan-300 flex items-center justify-between">
                <span>Voice Interface</span>
                <div className="flex space-x-2">
                  <Button
                    size="sm"
                    variant={activeVoiceMode === "interface" ? "default" : "outline"}
                    onClick={() => setActiveVoiceMode("interface")}
                    disabled={!voiceFeaturesEnabled}
                  >
                    Voice
                  </Button>
                  <Button
                    size="sm"
                    variant={activeVoiceMode === "commands" ? "default" : "outline"}
                    onClick={() => setActiveVoiceMode("commands")}
                    disabled={!voiceFeaturesEnabled}
                  >
                    Commands
                  </Button>
                </div>
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6">
              {!voiceFeaturesEnabled ? (
                <div className="text-center py-8 text-gray-400">
                  <span className="text-2xl mb-2 block">🔒</span>
                  <p>Voice features disabled</p>
                  <p className="text-sm">
                    {isEmergency ? "System in emergency mode" : "API not connected"}
                  </p>
                </div>
              ) : activeVoiceMode === "interface" ? (
                <VoiceInterface
                  onVoiceCommand={handleVoiceCommand}
                  isListening={isVoiceListening}
                />
              ) : (
                <VoiceCommandInterface onCommand={handleVoiceCommand} />
              )}
            </CardContent>
          </Card>

          {/* Audio Visualizer */}
          <Card className="bg-gray-800/50 border-gray-700">
            <CardHeader>
              <CardTitle className="text-cyan-300">Audio Visualizer</CardTitle>
            </CardHeader>
            <CardContent className="p-6">
              <div className="h-32">
                <AudioVisualizer isActive={isVoiceListening && voiceFeaturesEnabled} />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* System Status Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card className="bg-gray-800/50 border-gray-700">
            <CardHeader>
              <CardTitle className="text-cyan-300 text-sm">API Status</CardTitle>
            </CardHeader>
            <CardContent className="p-4">
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span>HTTP Client:</span>
                  <span className="text-gray-400">Checking...</span>
                </div>
                <div className="flex justify-between">
                  <span>WebSocket:</span>
                  <span className={isConnected ? "text-green-400" : "text-red-400"}>
                    {isConnected ? "Connected" : "Disconnected"}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gray-800/50 border-gray-700">
            <CardHeader>
              <CardTitle className="text-cyan-300 text-sm">Guardian Status</CardTitle>
            </CardHeader>
            <CardContent className="p-4">
              {guardianStatus ? (
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span>State:</span>
                    <span
                      className={
                        guardianStatus.status === "normal"
                          ? "text-green-400"
                          : ["degraded", "emergency"].includes(guardianStatus.status)
                            ? "text-red-400"
                            : "text-yellow-400"
                      }
                    >
                      {guardianStatus.status}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>RAM:</span>
                    <span>{guardianStatus.metrics.ram_pct}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span>CPU:</span>
                    <span>{guardianStatus.metrics.cpu_pct}%</span>
                  </div>
                </div>
              ) : (
                <div className="text-gray-400 text-sm">Loading...</div>
              )}
            </CardContent>
          </Card>

          <Card className="bg-gray-800/50 border-gray-700">
            <CardHeader>
              <CardTitle className="text-cyan-300 text-sm">System Actions</CardTitle>
            </CardHeader>
            <CardContent className="p-4">
              <div className="space-y-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setShowPerformanceHUD(!showPerformanceHUD)}
                  className="w-full"
                >
                  {showPerformanceHUD ? "Hide" : "Show"} Performance
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={isConnected ? disconnect : connect}
                  disabled={isConnecting}
                  className="w-full"
                >
                  {isConnected ? "Disconnect" : "Connect"}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Performance HUD */}
      <PerformanceHUD
        isVisible={showPerformanceHUD}
        onToggle={() => setShowPerformanceHUD(!showPerformanceHUD)}
      />
    </div>
  );
}
