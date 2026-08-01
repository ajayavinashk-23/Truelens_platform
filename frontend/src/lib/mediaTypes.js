import { Image, Video, AudioLines } from "lucide-react";

export const MEDIA_TYPES = {
  image: {
    id: "image",
    icon: Image,
    title: "Image",
    description:
      "JPG, PNG, or WEBP. Runs through the pretrained image deepfake detector.",
    accept: { "image/jpeg": [".jpg", ".jpeg"], "image/png": [".png"], "image/webp": [".webp"] },
    acceptAttr: "image/jpeg,image/png,image/webp",
    maxSizeMB: 25,
    hint: "PNG, JPG, or WEBP up to 25MB",
  },
  video: {
    id: "video",
    icon: Video,
    title: "Video",
    description:
      "MP4 or MOV. Frames are sampled roughly once per second and analyzed individually.",
    accept: { "video/mp4": [".mp4"], "video/quicktime": [".mov"] },
    acceptAttr: "video/mp4,video/quicktime",
    maxSizeMB: 200,
    hint: "MP4 or MOV up to 200MB",
  },
  audio: {
    id: "audio",
    icon: AudioLines,
    title: "Audio",
    description:
      "WAV or MP3. Checked for synthetic speech and voice-cloning artifacts.",
    accept: { "audio/wav": [".wav"], "audio/mpeg": [".mp3"] },
    acceptAttr: "audio/wav,audio/mpeg",
    maxSizeMB: 50,
    hint: "WAV or MP3 up to 50MB",
  },
};

export const MEDIA_TYPE_LIST = Object.values(MEDIA_TYPES);

export function isAcceptedFile(file, typeConfig) {
  return Object.keys(typeConfig.accept).includes(file.type);
}
