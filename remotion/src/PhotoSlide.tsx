import React from 'react';
import {AbsoluteFill, Img} from 'remotion';
import {FONT_FAMILY} from './constants';

// Mirrors the Python resize_contain_blurred approach: the whole photo stays
// fully visible (object-fit: contain) centered over a blurred, dimmed copy
// of itself that fills the frame, so there are no dead bars and nothing
// gets cropped out.
export const PhotoSlide: React.FC<{src: string; title?: string}> = ({src, title}) => {
	return (
		<AbsoluteFill style={{background: '#000', overflow: 'hidden'}}>
			<Img
				src={src}
				style={{
					position: 'absolute',
					inset: 0,
					width: '100%',
					height: '100%',
					objectFit: 'cover',
					filter: 'blur(45px) brightness(0.5)',
					transform: 'scale(1.15)',
				}}
			/>
			<Img
				src={src}
				style={{
					position: 'absolute',
					inset: 0,
					width: '100%',
					height: '100%',
					objectFit: 'contain',
				}}
			/>
			{title ? (
				// The title card only shows once at the very start of the ad, so
				// without this the product's name disappears for the entire
				// photo montage. Keep a compact strap of it visible over every
				// photo instead of just the intro card.
				<div
					style={{
						position: 'absolute',
						top: 0,
						left: 0,
						right: 0,
						padding: '36px 40px 24px',
						background: 'linear-gradient(180deg, rgba(0,0,0,0.55) 0%, rgba(0,0,0,0) 100%)',
						color: 'white',
						fontFamily: FONT_FAMILY,
						fontWeight: 800,
						fontSize: 34,
						textAlign: 'center',
						textShadow: '0 3px 10px rgba(0,0,0,0.5)',
					}}
				>
					{title}
				</div>
			) : null}
		</AbsoluteFill>
	);
};
