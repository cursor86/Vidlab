import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {FONT_FAMILY, GOLD, GOLD_GRADIENT} from './constants';

export const FeatureBullets: React.FC<{features: string[]}> = ({features}) => {
	const frame = useCurrentFrame();
	const opacity = interpolate(frame, [0, 20], [0, 1], {extrapolateRight: 'clamp'});

	return (
		<AbsoluteFill
			style={{
				background: GOLD_GRADIENT,
				justifyContent: 'center',
				alignItems: 'center',
			}}
		>
			<div
				style={{
					opacity,
					display: 'flex',
					flexDirection: 'column',
					gap: 30,
					padding: '0 55px',
				}}
			>
				{features.map((feature, i) => (
					<div
						key={i}
						style={{
							color: GOLD,
							fontFamily: FONT_FAMILY,
							fontWeight: 800,
							fontSize: 42,
							textAlign: 'center',
						}}
					>
						• {feature}
					</div>
				))}
			</div>
		</AbsoluteFill>
	);
};
