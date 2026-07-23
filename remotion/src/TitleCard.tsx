import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {FONT_FAMILY, HERO_GRADIENT} from './constants';

export const TitleCard: React.FC<{title: string}> = ({title}) => {
	const frame = useCurrentFrame();
	const opacity = interpolate(frame, [0, 15], [0, 1], {extrapolateRight: 'clamp'});

	return (
		<AbsoluteFill
			style={{
				background: HERO_GRADIENT,
				justifyContent: 'center',
				alignItems: 'center',
				padding: '0 70px',
			}}
		>
			<div
				style={{
					opacity,
					color: 'white',
					fontFamily: FONT_FAMILY,
					fontWeight: 800,
					fontSize: 64,
					textAlign: 'center',
					lineHeight: 1.25,
					textShadow: '0 6px 18px rgba(0,0,0,0.35)',
				}}
			>
				{title}
			</div>
		</AbsoluteFill>
	);
};
