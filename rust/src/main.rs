mod sim;
mod viz;

use clap::{Parser, ValueEnum};

#[derive(Debug, Clone, ValueEnum)]
enum Mode {
    Seq,
    Par,
    Viz,
}

#[derive(Parser, Debug)]
#[command(name = "brians-brain", about = "Brian's Brain cellular automaton")]
struct Args {
    /// seq | par | viz
    #[arg(long)]
    mode: Mode,

    #[arg(long, default_value = "100")]
    size: usize,

    #[arg(long, default_value = "100")]
    iterations: usize,

    #[arg(long, default_value = "42")]
    seed: u64,

    #[arg(long)]
    output: Option<String>,

    #[arg(long, default_value = "4")]
    threads: usize,

    #[arg(long)]
    input: Option<String>,

    #[arg(long, default_value = "50")]
    delay: u64,

    #[arg(long = "loop")]
    loop_anim: bool,
}

fn main() {
    let args = Args::parse();

    match args.mode {
        Mode::Seq => {
            sim::run_seq(args.size, args.iterations, args.seed, args.output.as_deref());
        }
        Mode::Par => {
            sim::run_par(
                args.size,
                args.iterations,
                args.seed,
                args.threads,
                args.output.as_deref(),
            );
        }
        Mode::Viz => {
            let input = args.input.expect("--input is required for --mode viz");
            viz::animate(&input, args.delay, args.loop_anim);
        }
    }
}
