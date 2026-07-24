import React from 'react';
import {AbsoluteFill, Img, interpolate, useCurrentFrame} from 'remotion';
import {DARK_PURPLE, FONT_FAMILY, GOLD, GOLD_GRADIENT} from './constants';

export const CtaEnd: React.FC<{cta: string; link: string; logoPath?: string}> = ({
	cta,
	link,
	logoPath,
}) => {
	const frame = useCurrentFrame();
	const opacity = interpolate(frame, [0, 20], [0, 1], {extrapolateRight: 'clamp'});

	return (
		<AbsoluteFill
			style={{
				background: GOLD_GRADIENT,
				justifyContent: 'center',
				alignItems: 'center',
				flexDirection: 'column',
				gap: 36,
				opacity,
			}}
		>
			{cta ? (
				<div
					style={{
						background: GOLD,
						color: DARK_PURPLE,
						fontFamily: FONT_FAMILY,
						fontWeight: 800,
						fontSize: 46,
						padding: '22px 70px',
						borderRadius: 10,
					}}
				>
					{cta}
				</div>
			) : null}
			{link ? (
				<div style={{color: GOLD, fontFamily: FONT_FAMILY, fontWeight: 700, fontSize: 22}}>
					{link}
				</div>
			) : null}
			{logoPath ? <Img src={logoPath} style={{height: 130, marginTop: 10}} /> : null}
		</AbsoluteFill>
	);
};
