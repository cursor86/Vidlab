import React from 'react';
import {AbsoluteFill, Img, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {DARK_PURPLE, FONT_FAMILY, GOLD} from './constants';

const INTRO_BG = 'radial-gradient(circle at 50% 38%, #3B2358 0%, #221336 45%, #170F22 100%)';

const SPARKLES = new Array(14).fill(0).map((_, i) => ({
	left: `${(i * 37 + 8) % 100}%`,
	top: `${(i * 53 + 12) % 100}%`,
	size: 3 + (i % 4),
	phase: (i * 0.6) % (Math.PI * 2),
	speed: 0.05 + (i % 3) * 0.02,
}));

export const TitleCard: React.FC<{title: string; logoPath?: string}> = ({title, logoPath}) => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();

	const bgOpacity = interpolate(frame, [0, 12], [0, 1], {extrapolateRight: 'clamp'});

	// Bouncy 3D flip-in: scale + rotateY settle over the first ~35 frames,
	// then a slow continuous wobble so the logo feels alive for the rest
	// of the 4s intro instead of going static.
	const entrance = spring({frame, fps, config: {damping: 12, mass: 0.7, stiffness: 90}});
	const scale = interpolate(entrance, [0, 1], [0.4, 1]);
	const flipRotateY = interpolate(entrance, [0, 1], [-150, 0]);
	const logoOpacity = interpolate(frame, [0, 18], [0, 1], {extrapolateRight: 'clamp'});

	const wobbleT = Math.max(0, frame - 35) / fps;
	const wobbleRotateY = flipRotateY + Math.sin(wobbleT * 1.3) * 6;
	const wobbleRotateX = Math.sin(wobbleT * 1.7 + 1) * 5;

	const glowPulse = 0.55 + 0.25 * Math.sin(frame / 14);

	// Diagonal shine sweep across the logo, like a light catching brushed metal.
	const shineX = interpolate(frame, [12, 55], [-160, 160], {
		extrapolateLeft: 'clamp',
		extrapolateRight: 'clamp',
	});

	const titleOpacity = interpolate(frame, [45, 70], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
	const titleY = interpolate(frame, [45, 70], [24, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

	return (
		<AbsoluteFill
			style={{
				background: INTRO_BG,
				opacity: bgOpacity,
				justifyContent: 'center',
				alignItems: 'center',
				flexDirection: 'column',
				overflow: 'hidden',
			}}
		>
			{SPARKLES.map((s, i) => {
				const twinkle = 0.2 + 0.8 * Math.abs(Math.sin(frame * s.speed + s.phase));
				return (
					<div
						key={i}
						style={{
							position: 'absolute',
							left: s.left,
							top: s.top,
							width: s.size,
							height: s.size,
							borderRadius: '50%',
							background: GOLD,
							opacity: twinkle * 0.7,
							boxShadow: `0 0 ${s.size * 3}px rgba(212,175,55,${twinkle * 0.6})`,
						}}
					/>
				);
			})}

			{logoPath ? (
				<div
					style={{
						position: 'relative',
						width: 300,
						height: 300,
						display: 'flex',
						alignItems: 'center',
						justifyContent: 'center',
						perspective: 900,
					}}
				>
					<div
						style={{
							position: 'absolute',
							width: 320,
							height: 320,
							borderRadius: '50%',
							background: 'radial-gradient(circle, rgba(212,175,55,0.55) 0%, rgba(212,175,55,0) 70%)',
							opacity: glowPulse,
							filter: 'blur(4px)',
						}}
					/>
					<div
						style={{
							position: 'relative',
							transformStyle: 'preserve-3d',
							transform: `scale(${scale}) rotateY(${wobbleRotateY}deg) rotateX(${wobbleRotateX}deg)`,
							opacity: logoOpacity,
							filter: 'drop-shadow(0 10px 30px rgba(0,0,0,0.5)) drop-shadow(0 0 26px rgba(212,175,55,0.5))',
						}}
					>
						<Img src={logoPath} style={{height: 210, width: 'auto', display: 'block'}} />
						<div
							style={{
								position: 'absolute',
								inset: 0,
								mixBlendMode: 'overlay',
								background:
									'linear-gradient(115deg, transparent 42%, rgba(255,255,255,0.85) 50%, transparent 58%)',
								transform: `translateX(${shineX}%)`,
							}}
						/>
					</div>
				</div>
			) : null}

			<div
				style={{
					marginTop: 28,
					opacity: titleOpacity,
					transform: `translateY(${titleY}px)`,
					color: 'white',
					fontFamily: FONT_FAMILY,
					fontWeight: 800,
					fontSize: 52,
					textAlign: 'center',
					lineHeight: 1.25,
					padding: '0 70px',
					textShadow: '0 6px 18px rgba(0,0,0,0.45)',
				}}
			>
				{title}
			</div>

			{/* Subtle floor reflection tint so the dark background doesn't read flat */}
			<div
				style={{
					position: 'absolute',
					bottom: 0,
					left: 0,
					right: 0,
					height: '30%',
					background: `linear-gradient(180deg, transparent 0%, ${DARK_PURPLE} 100%)`,
					opacity: 0.6,
				}}
			/>
		</AbsoluteFill>
	);
};
