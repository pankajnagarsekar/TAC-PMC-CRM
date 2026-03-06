"use client";

import React, { useRef, useState, useEffect } from "react";
import { Play, Pause, RotateCcw, Volume2 } from "lucide-react";

interface AudioPlayerProps {
  src: string;
}

export default function AudioPlayer({ src }: AudioPlayerProps) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(80);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const updateTime = () => setCurrentTime(audio.currentTime);
    const updateDuration = () => setDuration(audio.duration);
    const onEnded = () => setIsPlaying(false);

    audio.addEventListener("timeupdate", updateTime);
    audio.addEventListener("loadedmetadata", updateDuration);
    audio.addEventListener("ended", onEnded);

    return () => {
      audio.removeEventListener("timeupdate", updateTime);
      audio.removeEventListener("loadedmetadata", updateDuration);
      audio.removeEventListener("ended", onEnded);
    };
  }, [src]);

  const togglePlay = () => {
    if (audioRef.current) {
      if (isPlaying) {
        audioRef.current.pause();
      } else {
        audioRef.current.play();
      }
      setIsPlaying(!isPlaying);
    }
  };

  const reset = () => {
    if (audioRef.current) {
      audioRef.current.currentTime = 0;
      if (!isPlaying) {
        audioRef.current.play();
        setIsPlaying(true);
      }
    }
  };

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = Number(e.target.value);
    setVolume(val);
    if (audioRef.current) {
      audioRef.current.volume = val / 100;
    }
  };

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = Number(e.target.value);
    setCurrentTime(val);
    if (audioRef.current) {
      audioRef.current.currentTime = val;
    }
  };

  const formatTime = (time: number) => {
    if (isNaN(time)) return "0:00";
    const mins = Math.floor(time / 60);
    const secs = Math.floor(time % 60);
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  return (
    <div className="w-full space-y-5 p-6 bg-slate-950 border border-slate-800 rounded-[2rem] shadow-inner shadow-black/40">
      <audio ref={audioRef} src={src} preload="metadata" />
      
      <div className="flex flex-col sm:flex-row items-center gap-6">
        <div className="flex items-center gap-3">
          <button 
            onClick={togglePlay} 
            className="h-12 w-12 rounded-full bg-orange-600 hover:bg-orange-500 text-white flex items-center justify-center transition-all shadow-lg shadow-orange-950/40 active:scale-90"
          >
            {isPlaying ? <Pause size={20} fill="currentColor" /> : <Play size={20} className="ml-1" fill="currentColor" />}
          </button>
          <button 
            onClick={reset} 
            className="h-10 w-10 rounded-full bg-slate-900 border border-slate-800 text-slate-400 hover:text-white flex items-center justify-center transition-colors"
            title="Reset"
          >
            <RotateCcw size={16} />
          </button>
        </div>
        
        <div className="flex-1 w-full space-y-2">
          <div className="relative h-1.5 w-full bg-slate-900 rounded-full overflow-hidden border border-slate-800">
             <div 
               className="absolute top-0 left-0 h-full bg-orange-600 shadow-[0_0_10px_rgba(234,88,12,0.5)]" 
               style={{ width: `${(currentTime / (duration || 1)) * 100}%` }} 
             />
             <input
               type="range"
               min="0"
               max={duration || 0}
               value={currentTime}
               onChange={handleSeek}
               className="absolute top-0 left-0 w-full h-full opacity-0 cursor-pointer z-10"
             />
          </div>
          <div className="flex justify-between text-[10px] text-slate-500 font-bold uppercase tracking-widest px-1">
            <span>{formatTime(currentTime)}</span>
            <span>{formatTime(duration)}</span>
          </div>
        </div>

        <div className="flex items-center gap-3 w-32 bg-slate-900/50 px-3 py-1.5 rounded-full border border-slate-800/50">
          <Volume2 size={14} className="text-slate-500" />
          <input 
            type="range"
            min="0"
            max="100"
            value={volume}
            onChange={handleVolumeChange}
            className="w-full h-1 bg-slate-800 rounded-xl accent-orange-600 cursor-pointer"
          />
        </div>
      </div>
    </div>
  );
}
