import * as core from '@actions/core';
import * as github from '@actions/github';
import { runAnalyzer, Report } from './analyzer';
import { reportHallucinations } from './reporter';

async function run(): Promise<void> {
  try {
    const token = core.getInput('github-token', { required: true });
    const threshold = core.getInput('severity-threshold') || 'MEDIUM';
    const failOnHallucination = core.getInput('fail-on-hallucination') === 'true';

    core.info('Fetching changed files...');

    const files = await getChangedFiles(token);
    if (files.length === 0) {
      core.info('No Python or JavaScript/TypeScript files changed.');
      return;
    }

    core.info(`Analyzing ${files.length} file(s) for hallucinations...`);
    const reports: Report[] = await runAnalyzer(files);

    core.info('Publishing report and evaluating thresholds...');
    await reportHallucinations(token, reports, threshold, failOnHallucination);

  } catch (error: any) {
    core.setFailed(error.message);
  }
}

async function getChangedFiles(token: string): Promise<string[]> {
  const octokit = github.getOctokit(token);
  const context = github.context;

  if (!context.payload.pull_request) {
    // If not a PR, we could potentially scan the whole repo context, 
    // but for now we only support PRs.
    core.info('Not a PR, no changed files extracted.');
    return [];
  }

  const { owner, repo } = context.repo;
  const pull_number = context.payload.pull_request.number;

  const { data: files } = await octokit.rest.pulls.listFiles({
    owner,
    repo,
    pull_number,
    per_page: 100
  });

  const supportedExtensions = ['.js', '.jsx', '.ts', '.tsx', '.py'];
  
  return files
    .filter(f => f.status !== 'removed' && supportedExtensions.some(ext => f.filename.endsWith(ext)))
    .map(f => f.filename);
}

// Start the action
run();
