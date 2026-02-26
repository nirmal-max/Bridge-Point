/* ─── Bridge Point — WebRTC Peer Connection Manager ─── */

export interface ICEServer {
  urls: string;
  username?: string;
  credential?: string;
}

export interface WebRTCCallbacks {
  onRemoteStream: (stream: MediaStream) => void;
  onICECandidate: (candidate: RTCIceCandidateInit) => void;
  onConnectionStateChange: (state: RTCPeerConnectionState) => void;
  onICEConnectionStateChange?: (state: RTCIceConnectionState) => void;
}

const DEFAULT_ICE_SERVERS: ICEServer[] = [
  { urls: "stun:stun.l.google.com:19302" },
  { urls: "stun:stun1.l.google.com:19302" },
  { urls: "stun:stun2.l.google.com:19302" },
];

export class WebRTCManager {
  private pc: RTCPeerConnection | null = null;
  private localStream: MediaStream | null = null;
  private callbacks: WebRTCCallbacks;
  private iceServers: ICEServer[];

  constructor(callbacks: WebRTCCallbacks, iceServers?: ICEServer[]) {
    this.callbacks = callbacks;
    this.iceServers = iceServers || DEFAULT_ICE_SERVERS;
  }

  /**
   * Initialize the peer connection and acquire local microphone.
   */
  async initialize(): Promise<void> {
    // Get microphone access
    this.localStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
      video: false,
    });

    // Create RTCPeerConnection
    this.pc = new RTCPeerConnection({
      iceServers: this.iceServers.map((s) => ({
        urls: s.urls,
        username: s.username,
        credential: s.credential,
      })),
    });

    // Add local tracks to the connection
    this.localStream.getTracks().forEach((track) => {
      this.pc!.addTrack(track, this.localStream!);
    });

    // Handle remote tracks
    this.pc.ontrack = (event) => {
      if (event.streams && event.streams[0]) {
        this.callbacks.onRemoteStream(event.streams[0]);
      }
    };

    // Handle ICE candidates
    this.pc.onicecandidate = (event) => {
      if (event.candidate) {
        this.callbacks.onICECandidate(event.candidate.toJSON());
      }
    };

    // Connection state changes
    this.pc.onconnectionstatechange = () => {
      if (this.pc) {
        this.callbacks.onConnectionStateChange(this.pc.connectionState);
      }
    };

    // ICE connection state changes
    this.pc.oniceconnectionstatechange = () => {
      if (this.pc && this.callbacks.onICEConnectionStateChange) {
        this.callbacks.onICEConnectionStateChange(this.pc.iceConnectionState);
      }
    };
  }

  /**
   * Create an SDP offer (caller side).
   */
  async createOffer(): Promise<RTCSessionDescriptionInit> {
    if (!this.pc) throw new Error("PeerConnection not initialized");
    const offer = await this.pc.createOffer();
    await this.pc.setLocalDescription(offer);
    return offer;
  }

  /**
   * Create an SDP answer (callee side).
   */
  async createAnswer(
    remoteSDP: RTCSessionDescriptionInit
  ): Promise<RTCSessionDescriptionInit> {
    if (!this.pc) throw new Error("PeerConnection not initialized");
    await this.pc.setRemoteDescription(new RTCSessionDescription(remoteSDP));
    const answer = await this.pc.createAnswer();
    await this.pc.setLocalDescription(answer);
    return answer;
  }

  /**
   * Set remote SDP answer (caller side, after receiving answer).
   */
  async setRemoteAnswer(remoteSDP: RTCSessionDescriptionInit): Promise<void> {
    if (!this.pc) throw new Error("PeerConnection not initialized");
    await this.pc.setRemoteDescription(new RTCSessionDescription(remoteSDP));
  }

  /**
   * Add a remote ICE candidate.
   */
  async addICECandidate(candidate: RTCIceCandidateInit): Promise<void> {
    if (!this.pc) throw new Error("PeerConnection not initialized");
    try {
      await this.pc.addIceCandidate(new RTCIceCandidate(candidate));
    } catch (err) {
      console.warn("Failed to add ICE candidate:", err);
    }
  }

  /**
   * Toggle local microphone mute.
   */
  toggleMute(): boolean {
    if (!this.localStream) return false;
    const audioTrack = this.localStream.getAudioTracks()[0];
    if (audioTrack) {
      audioTrack.enabled = !audioTrack.enabled;
      return !audioTrack.enabled; // true = muted
    }
    return false;
  }

  /**
   * Get current mute state.
   */
  get isMuted(): boolean {
    if (!this.localStream) return false;
    const audioTrack = this.localStream.getAudioTracks()[0];
    return audioTrack ? !audioTrack.enabled : false;
  }

  /**
   * Clean up all resources.
   */
  cleanup(): void {
    // Stop local media tracks
    if (this.localStream) {
      this.localStream.getTracks().forEach((track) => track.stop());
      this.localStream = null;
    }

    // Close peer connection
    if (this.pc) {
      this.pc.close();
      this.pc = null;
    }
  }

  get connectionState(): RTCPeerConnectionState | null {
    return this.pc?.connectionState || null;
  }
}
