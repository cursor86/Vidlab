import React from 'react';
import {Audio} from 'remotion';
import {TransitionSeries, linearTiming} from '@remotion/transitions';
import {fade} from '@remotion/transitions/fade';
import {z} from 'zod';
import {TitleCard} from './TitleCard';
import {PhotoSlide} from './PhotoSlide';
import {FeatureBullets} from './FeatureBullets';
import {CtaEnd} from './CtaEnd';
import {getAudioDurationSeconds} from './audio-duration';
import {
	CTA_SECONDS,
	FEATURES_SECONDS,
	FPS,
	MAX_DURATION_SECONDS,
	MIN_DURATION_SECONDS,
	PHOTO_SECONDS_EACH,
	TITLE_SECONDS,
	TRANSITION_SECONDS,
} from './constants';

export const montageSchema = z.object({
	title: z.string(),
	features: z.array(z.string()),
	cta: z.string(),
	link: z.string(),
	images: z.array(z.string()),
	music: z.string(),
	logoPath: z.string().optional(),
	// Injected by calculateMontageMetadata (computed in Node from the actual
	// audio duration) so the component - which renders in the browser and
	// can't read the filesystem itself - knows exactly how many frames it has
	// to fill. Without this the photo section can't be sized correctly and
	// the CTA card can end up pushed past the end of the video.
	totalFrames: z.number().optional(),
});

export type MontageProps = z.infer<typeof montageSchema>;

const secondsToFrames = (seconds: number) => Math.round(seconds * FPS);

// Same budgeting approach as the Python backend: reserve frames for the
// title/features/CTA cards, then fill whatever's left with photos, cycling
// through the uploaded images if there are more frames than images.
export const calculateMontageMetadata = async ({props}: {props: MontageProps}) => {
	const audioDuration = props.music ? await getAudioDurationSeconds(props.music) : MIN_DURATION_SECONDS;
	const totalSeconds = Math.max(MIN_DURATION_SECONDS, Math.min(audioDuration, MAX_DURATION_SECONDS));
	const durationInFrames = secondsToFrames(totalSeconds);

	return {durationInFrames, props: {...props, totalFrames: durationInFrames}};
};

type Segment =
	| {kind: 'title'; frames: number; title: string}
	| {kind: 'photo'; frames: number; src: string; title?: string}
	| {kind: 'features'; frames: number; features: string[]}
	| {kind: 'cta'; frames: number; cta: string; link: string; logoPath?: string};

export const MontageAd: React.FC<MontageProps> = ({
	title,
	features,
	cta,
	link,
	images,
	music,
	logoPath,
	totalFrames,
}) => {
	const titleFrames = title ? secondsToFrames(TITLE_SECONDS) : 0;
	const ctaFrames = secondsToFrames(CTA_SECONDS);
	const featuresFrames = features.length > 0 ? secondsToFrames(FEATURES_SECONDS) : 0;
	const transitionFrames = secondsToFrames(TRANSITION_SECONDS);
	const photoFramesEach = secondsToFrames(PHOTO_SECONDS_EACH);

	// Falls back to the max only for the Remotion Studio preview, where
	// calculateMetadata may not have run yet against real props.
	const effectiveTotalFrames = totalFrames ?? secondsToFrames(MAX_DURATION_SECONDS);
	const photoBudgetFrames = Math.max(
		photoFramesEach,
		effectiveTotalFrames - titleFrames - ctaFrames - featuresFrames
	);
	const slotCount = images.length > 0 ? Math.max(1, Math.ceil(photoBudgetFrames / photoFramesEach)) : 0;

	const segments: Segment[] = [];
	if (title) segments.push({kind: 'title', frames: titleFrames, title});
	for (let i = 0; i < slotCount; i++) {
		segments.push({kind: 'photo', frames: photoFramesEach, src: images[i % images.length], title});
	}
	if (featuresFrames > 0) segments.push({kind: 'features', frames: featuresFrames, features});
	segments.push({kind: 'cta', frames: ctaFrames, cta, link, logoPath});

	// TransitionSeries overlaps every adjacent pair of sequences by the
	// transition's duration, so the rendered total is shorter than the raw
	// sum of segment lengths. Extend the last segment (the CTA) by that
	// overlap so the video always fills exactly effectiveTotalFrames instead
	// of ending a bit short with silent/blank trailing frames.
	const transitionsCount = Math.max(0, segments.length - 1);
	const rawTotal = segments.reduce((sum, s) => sum + s.frames, 0);
	const deficit = effectiveTotalFrames - (rawTotal - transitionsCount * transitionFrames);
	if (deficit > 0) {
		segments[segments.length - 1].frames += deficit;
	}

	return (
		<>
			{music ? <Audio src={music} /> : null}
			<TransitionSeries>
				{segments.map((segment, i) => (
					<React.Fragment key={i}>
						<TransitionSeries.Sequence durationInFrames={segment.frames}>
							{segment.kind === 'title' ? <TitleCard title={segment.title} /> : null}
							{segment.kind === 'photo' ? <PhotoSlide src={segment.src} title={segment.title} /> : null}
							{segment.kind === 'features' ? <FeatureBullets features={segment.features} /> : null}
							{segment.kind === 'cta' ? (
								<CtaEnd cta={segment.cta} link={segment.link} logoPath={segment.logoPath} />
							) : null}
						</TransitionSeries.Sequence>
						{i < segments.length - 1 ? (
							<TransitionSeries.Transition
								presentation={fade()}
								timing={linearTiming({durationInFrames: transitionFrames})}
							/>
						) : null}
					</React.Fragment>
				))}
			</TransitionSeries>
		</>
	);
};
