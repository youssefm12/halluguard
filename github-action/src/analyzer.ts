import * as exec from '@actions/exec';
import * as path from 'path';

export interface HallucinationItem {
  line: number;
  type: string;
  token: string;
  explanation: string;
  suggestion: string;
  severity: string;
}

export interface Report {
  file: string;
  risk_score: number;
  confidence: string;
  hallucinations: HallucinationItem[];
  suggestions: any[];
  error?: string;
}

export async function runAnalyzer(files: string[]): Promise<Report[]> {
  if (files.length === 0) {
    return [];
  }

  // Find the path to the python CLI script.
  // When running in the GitHub Action, the workspace root contains the `cli/analyzer.py`
  const workspaceDir = process.env.GITHUB_WORKSPACE || process.cwd();
  const scriptPath = path.join(workspaceDir, 'cli', 'analyzer.py');

  let stdout = '';
  let stderr = '';

  const options: exec.ExecOptions = {
    env: {
      ...process.env,
      PYTHONPATH: workspaceDir
    },
    listeners: {
      stdout: (data: Buffer) => {
        stdout += data.toString();
      },
      stderr: (data: Buffer) => {
        stderr += data.toString();
      }
    },
    silent: true // Do not echo stdout directly to the action log unless we want to
  };

  try {
    await exec.exec('python', [scriptPath, ...files], options);
  } catch (error) {
    console.error(`Error running python script: ${error}`);
    if (stderr) {
      console.error(`Script stderr: ${stderr}`);
    }
    throw new Error('Failed to run HalluGuard analysis script.');
  }

  try {
    // Parse the JSON array from stdout
    const parseableOutput = extractJsonArray(stdout);
    if (!parseableOutput) {
      throw new Error("No JSON array found in stdout.");
    }
    const reports: Report[] = JSON.parse(parseableOutput);
    return reports;
  } catch (err: any) {
    console.error('Failed to parse analysis output.');
    console.error(`Stdout: ${stdout}`);
    throw new Error(`Parse error: ${err.message}`);
  }
}

/** 
 * Safely extracts the JSON array from stdout in case the script 
 * output extraneous logging/warnings before the JSON output. 
 */
function extractJsonArray(out: string): string | null {
  const startIdx = out.indexOf('[');
  const endIdx = out.lastIndexOf(']');
  if (startIdx >= 0 && endIdx >= 0 && endIdx > startIdx) {
    return out.substring(startIdx, endIdx + 1);
  }
  return null;
}
