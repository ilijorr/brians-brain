use std::fs::File;
use std::io::{BufReader, Read, Write, stdout};
use std::time::Duration;

use crossterm::{
    cursor::{Hide, MoveTo, Show},
    event::{self, Event, KeyCode},
    execute, queue,
    style::{Color, Print, ResetColor, SetBackgroundColor},
    terminal::{self, EnterAlternateScreen, LeaveAlternateScreen},
};

pub fn load_bin(path: &str) -> (usize, Vec<Vec<u8>>) {
    let mut f = BufReader::new(File::open(path).expect("cannot open input file"));
    let mut buf = [0u8; 8];

    f.read_exact(&mut buf).unwrap();
    let n = u64::from_le_bytes(buf) as usize;

    f.read_exact(&mut buf).unwrap();
    let num_frames = u64::from_le_bytes(buf) as usize;

    let mut frames = Vec::with_capacity(num_frames);
    for _ in 0..num_frames {
        let mut frame = vec![0u8; n * n];
        f.read_exact(&mut frame).unwrap();
        frames.push(frame);
    }
    (n, frames)
}

fn cell_color(cell: u8) -> Color {
    match cell {
        0 => Color::Black,      // Off   -> black
        1 => Color::White,      // On    -> white
        2 => Color::Blue,       // Dying -> blue
        _ => Color::Black,
    }
}

pub fn animate(path: &str, delay_ms: u64, loop_anim: bool) {
    let (n, frames) = load_bin(path);
    let num_frames = frames.len();

    let mut out = stdout();
    let (term_cols, term_rows) = terminal::size().unwrap_or((80, 24));

    let display_cols = ((term_cols / 2) as usize).min(n);
    let display_rows = ((term_rows - 1) as usize).min(n);

    execute!(out, EnterAlternateScreen, Hide).unwrap();
    terminal::enable_raw_mode().unwrap();

    let orig_hook = std::panic::take_hook();
    std::panic::set_hook(Box::new(move |info| {
        let _ = terminal::disable_raw_mode();
        let _ = execute!(std::io::stdout(), Show, LeaveAlternateScreen, ResetColor);
        orig_hook(info);
    }));

    let delay = Duration::from_millis(delay_ms);

    'outer: loop {
        for (idx, frame) in frames.iter().enumerate() {
            if event::poll(Duration::ZERO).unwrap() {
                if let Event::Key(key) = event::read().unwrap() {
                    if matches!(key.code, KeyCode::Char('q') | KeyCode::Esc) {
                        break 'outer;
                    }
                }
            }

            for row in 0..display_rows {
                queue!(out, MoveTo(0, row as u16)).unwrap();
                for col in 0..display_cols {
                    queue!(
                        out,
                        SetBackgroundColor(cell_color(frame[row * n + col])),
                        Print("  ")
                    )
                    .unwrap();
                }
                queue!(out, ResetColor).unwrap();
            }

            queue!(
                out,
                MoveTo(0, display_rows as u16),
                ResetColor,
                Print(format!(
                    "frame {}/{} | {}x{} | q / Esc to quit   ",
                    idx + 1,
                    num_frames,
                    n,
                    n
                ))
            )
            .unwrap();

            out.flush().unwrap();
            std::thread::sleep(delay);
        }

        if !loop_anim {
            break;
        }
    }

    terminal::disable_raw_mode().unwrap();
    execute!(out, Show, LeaveAlternateScreen, ResetColor).unwrap();
}
