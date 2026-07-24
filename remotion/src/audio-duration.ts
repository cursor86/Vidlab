import {getAudioDurationInSeconds} from '@remotion/media-utils';

// calculateMetadata runs inside Remotion's headless-Chrome evaluation, not
// plain Node, so this has to use a browser-safe way of reading duration
// (an actual <audio> element under the hood) rather than shelling out to
// ffprobe like the Python backend does.
export const getAudioDurationSeconds = (audioPath: string): Promise<number> => {
	return getAudioDurationInSeconds(audioPath);
};
