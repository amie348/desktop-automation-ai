"""Windows implementation of the bash tool using cmd.exe"""

import asyncio
import os
import subprocess
from typing import Any, Literal, TypedDict

from anthropic.types.beta import BetaToolParam
from asyncio.subprocess import PIPE
from .base import BaseAnthropicTool, ToolError, ToolResult


class AsyncWindowsShell:
    """Async wrapper for Windows command shell."""
    
    def __init__(self):
        self._process = None
        self._stderr_task = None
        self._stdout_task = None

    async def start(self):
        """Start a Windows command shell process."""
        # We don't need to maintain a persistent shell process
        pass

    async def _run_system_command(self, command: str) -> tuple[int, str, str]:
        """Execute a Windows system command."""
        try:
            # Run the command with subprocess.run
            process = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True,  # Required for system commands
                creationflags=subprocess.CREATE_NO_WINDOW,
                timeout=30,  # System commands might take longer
                text=True,
                encoding='utf-8',
                errors='ignore'
            )
            
            if process.returncode == 0:
                return 0, process.stdout, process.stderr
            else:
                error_msg = process.stderr if process.stderr else process.stdout
                return process.returncode, f"Command failed with error: {error_msg}", process.stderr
                
        except subprocess.TimeoutExpired:
            return 1, "Command timed out after 30 seconds", ""
        except Exception as e:
            return 1, f"Failed to execute system command: {str(e)}", ""

    async def _run_network_command(self, command: str) -> tuple[int, str, str]:
        """Execute a network command directly using synchronous subprocess."""
        try:
            # Use cmd.exe explicitly for network commands
            full_command = f'cmd.exe /c {command}'
            
            # Run the command with subprocess.run
            process = subprocess.run(
                full_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW,
                timeout=10,  # 10 second timeout
                text=True,   # Automatically decode output as text
                encoding='utf-8',  # Try UTF-8 first
                errors='ignore'  # Ignore any decoding errors
            )
            
            if process.returncode == 0:
                return 0, process.stdout, process.stderr
            else:
                error_msg = process.stderr if process.stderr else process.stdout
                return process.returncode, f"Command failed with error: {error_msg}", process.stderr
                
        except subprocess.TimeoutExpired:
            return 1, "Command timed out after 10 seconds", ""
        except Exception as e:
            return 1, f"Failed to execute command: {str(e)}", ""

    async def _run_system_cmd(self, command: str) -> tuple[int, str, str]:
        """Execute a Windows system command."""
        try:
            # Define common system32 paths
            system32_path = os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'System32')
            cmd_path = os.path.join(system32_path, 'cmd.exe')
            
            # Get the command base name
            base_cmd = command.split()[0].lower()
            
            # If it's a system command, try to find its full path
            if base_cmd in ['systeminfo', 'wmic', 'tasklist']:
                cmd_exe = os.path.join(system32_path, f"{base_cmd}.exe")
                if os.path.exists(cmd_exe):
                    # Replace the command with its full path
                    command = f"{cmd_exe} {' '.join(command.split()[1:])}"
            
            # Create the full command with proper environment setup
            full_command = f'"{cmd_path}" /c "{command}"'
            
            # Set up the environment with system32 path
            env = os.environ.copy()
            env['PATH'] = f"{system32_path};{env.get('PATH', '')}"
            
            # Run the command synchronously
            result = subprocess.run(
                full_command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='ignore',
                creationflags=subprocess.CREATE_NO_WINDOW,
                env=env,
                cwd=system32_path  # Run from System32 directory
            )
            
            if result.returncode == 0:
                return 0, result.stdout, result.stderr
            else:
                error = result.stderr if result.stderr else result.stdout
                return result.returncode, f"Command failed: {error}", result.stderr
        except Exception as e:
            error_msg = f"""Failed to execute system command:
            Command: {command}
            Error: {str(e)}
            System32 Path: {system32_path}
            Command Exists: {os.path.exists(cmd_path)}"""
            return 1, error_msg, ""

    async def _run_web_command(self, command: str) -> tuple[int, str, str]:
        """Execute web commands like curl, wget with longer timeouts."""
        try:
            # Check if curl is available, if not suggest alternatives
            base_cmd = command.split()[0].lower()
            
            if base_cmd == 'curl':
                # First try to run curl directly
                try:
                    # Show exactly what command is being executed for debugging
                    print(f"DEBUG: Executing curl command: {command}")
                    
                    process = subprocess.run(
                        command,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        shell=True,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                        timeout=60,  # 60 second timeout for web requests
                        text=True,
                        encoding='utf-8',
                        errors='ignore'
                    )
                    
                    if process.returncode == 0:
                        return 0, process.stdout, process.stderr
                    else:
                        error_msg = process.stderr if process.stderr else process.stdout
                        
                        # Check for specific curl errors and provide alternatives
                        if "URL rejected: Bad hostname" in error_msg or "Could not resolve host" in error_msg:
                            # Extract URL and file path from command for PowerShell alternative
                            import re
                            url_match = re.search(r'https?://[^\s"]+', command)
                            file_match = re.search(r'file=@([^\s"\']+)', command)
                            
                            if url_match and file_match:
                                url = url_match.group(0)
                                file_path = file_match.group(1)
                                
                                # Create PowerShell multipart form data command
                                powershell_cmd = f'''powershell -Command "
                                $filePath = '{file_path}'
                                $url = '{url}'
                                $boundary = [System.Guid]::NewGuid().ToString()
                                $bodyLines = @()
                                $bodyLines += '--' + $boundary
                                $bodyLines += 'Content-Disposition: form-data; name=\\"file\\"; filename=\\"' + [System.IO.Path]::GetFileName($filePath) + '\\"'
                                $bodyLines += 'Content-Type: application/octet-stream'
                                $bodyLines += ''
                                $fileBytes = [System.IO.File]::ReadAllBytes($filePath)
                                $bodyLines += [System.Text.Encoding]::GetEncoding('iso-8859-1').GetString($fileBytes)
                                $bodyLines += '--' + $boundary + '--'
                                $body = $bodyLines -join '`r`n'
                                try {{
                                    $response = Invoke-WebRequest -Uri $url -Method POST -Body $body -ContentType \\"multipart/form-data; boundary=$boundary\\"
                                    Write-Output \\"Upload successful. Status: $($response.StatusCode)\\"
                                    Write-Output $response.Content
                                }} catch {{
                                    Write-Error \\"PowerShell upload failed: $($_.Exception.Message)\\"
                                }}
                                "'''
                                
                                return process.returncode, f"""CURL FAILED with hostname error.

                                        EXECUTED COMMAND: {command}
                                        CURL ERROR: {error_msg}

                                        SOLUTION 1 - Try this PowerShell alternative:
                                        {powershell_cmd}

                                        SOLUTION 2 - Test DNS resolution:
                                        nslookup {url.split('/')[2]}

                                        SOLUTION 3 - Test basic curl:
                                        curl -I {url.split('/')[0]}//{url.split('/')[2]}

                                        DEBUG INFO:
                                        - Original command: {command}
                                        - Detected URL: {url}
                                        - Detected file: {file_path}
                                        - File exists: {os.path.exists(file_path)}
                                """, process.stderr
                            else:
                                return process.returncode, f"""CURL FAILED with hostname error.

                                    EXECUTED COMMAND: {command}
                                    CURL ERROR: {error_msg}

                                    Could not parse URL or file path from command. Please check the command format.
                                    Expected format: curl -X POST -F "file=@/path/to/file" https://url.com/endpoint
                                """, process.stderr
                        
                        return process.returncode, f"""CURL FAILED:

                                EXECUTED COMMAND: {command}
                                ERROR MESSAGE: {error_msg}

                                Try running the command manually in cmd to verify it works.
                        """, process.stderr
                        
                except FileNotFoundError:
                    # curl not found, suggest alternatives
                    import re
                    url_match = re.search(r'https?://[^\s"]+', command)
                    file_match = re.search(r'file=@([^\s"\']+)', command)
                    
                    if url_match and file_match:
                        url = url_match.group(0)
                        file_path = file_match.group(1)
                        
                        powershell_alternative = f'''powershell -Command "
                                    $filePath = '{file_path}'
                                    $url = '{url}'
                                    $boundary = [System.Guid]::NewGuid().ToString()
                                    $bodyLines = @()
                                    $bodyLines += '--' + $boundary
                                    $bodyLines += 'Content-Disposition: form-data; name=\\"file\\"; filename=\\"' + [System.IO.Path]::GetFileName($filePath) + '\\"'
                                    $bodyLines += 'Content-Type: application/octet-stream'
                                    $bodyLines += ''
                                    $fileBytes = [System.IO.File]::ReadAllBytes($filePath)
                                    $bodyLines += [System.Text.Encoding]::GetEncoding('iso-8859-1').GetString($fileBytes)
                                    $bodyLines += '--' + $boundary + '--'
                                    $body = $bodyLines -join '`r`n'
                                    $response = Invoke-WebRequest -Uri $url -Method POST -Body $body -ContentType \\"multipart/form-data; boundary=$boundary\\"
                                    Write-Output \\"Upload successful. Status: $($response.StatusCode)\\"
                                    "'''
                        
                        return 1, f"""CURL NOT FOUND - curl is not installed or not in PATH.

                            SOLUTION 1 - Use this PowerShell alternative (ready to run):
                            {powershell_alternative}

                            SOLUTION 2 - Install curl:
                            winget install curl.curl

                            SOLUTION 3 - Install curl via chocolatey:
                            choco install curl

                            DEBUG INFO:
                            - Detected URL: {url}
                            - Detected file: {file_path}
                            - File exists: {os.path.exists(file_path)}
                        """, ""
                    else:
                        return 1, """CURL NOT FOUND - curl is not installed or not in PATH.

SOLUTIONS:
1. Install curl: winget install curl.curl
2. Install via chocolatey: choco install curl  
3. Use PowerShell: powershell Invoke-WebRequest -Uri "URL" -Method POST -InFile "file.zip"
                        """, ""
                except subprocess.TimeoutExpired:
                    return 1, "Curl command timed out after 60 seconds", ""
                    
            elif base_cmd == 'wget':
                # wget is typically not available on Windows, suggest alternatives
                return 1, """wget is not available on Windows by default.
                
Alternatives:
1. Use PowerShell: powershell Invoke-WebRequest -Uri "URL" -OutFile "filename"
2. Use curl: curl -O "URL"
3. Use certutil: certutil -urlcache -split -f "URL" "filename"
                """, ""
                
            elif base_cmd == 'certutil':
                # certutil is available on Windows
                process = subprocess.run(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    shell=True,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    timeout=60,
                    text=True,
                    encoding='utf-8',
                    errors='ignore'
                )
                
                if process.returncode == 0:
                    return 0, process.stdout, process.stderr
                else:
                    error_msg = process.stderr if process.stderr else process.stdout
                    return process.returncode, f"Certutil command failed: {error_msg}", process.stderr
            
            # Default handling for other web commands
            process = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
                timeout=60,
                text=True,
                encoding='utf-8',
                errors='ignore'
            )
            
            if process.returncode == 0:
                return 0, process.stdout, process.stderr
            else:
                error_msg = process.stderr if process.stderr else process.stdout
                return process.returncode, f"Web command failed: {error_msg}", process.stderr
                
        except subprocess.TimeoutExpired:
            return 1, "Web command timed out after 60 seconds", ""
        except Exception as e:
            return 1, f"Failed to execute web command: {str(e)}", ""

    async def run(self, command: str, _skip_compound: bool = False) -> tuple[int, str, str]:
        """Run a command in the shell and return exit code, stdout, and stderr."""
        try:
            print(f"DEBUG: Original command: {command}, skip_compound: {_skip_compound}")
            
            # Convert Unix-style paths and commands to Windows equivalents
            converted_command = self._convert_unix_to_windows(command)
            print(f"DEBUG: Converted command: {converted_command}")
            
            # Check for cd commands in compound commands
            if not _skip_compound and ('&&' in converted_command or '||' in converted_command):
                # Check if any part of the compound command contains cd
                parts = converted_command.replace('&&', '||').split('||')
                for part in parts:
                    part_cmd = part.strip().split()[0].lower() if part.strip() else ''
                    if part_cmd in ['cd', 'chdir', 'pwd']:
                        return 1, """Please don't use 'cd' or 'pwd' commands in compound statements. Instead, use absolute paths.

                        For example:
                        - Instead of: cd "C:\\Users\\ahmad\\Downloads" && dir
                        - Use: dir "C:\\Users\\ahmad\\Downloads"

                        - Instead of: cd "C:\\path" && mkdir newfolder  
                        - Use: mkdir "C:\\path\\newfolder"

                        This approach is more reliable and doesn't require changing directories.""", ""
                
                print("DEBUG: Processing as compound command")
                return await self._run_compound_command(converted_command)
            
            # Get base command for routing
            base_cmd = converted_command.split()[0].lower()
            print(f"DEBUG: Base command: {base_cmd}")
            
            # Handle system commands
            system_commands = {
                'systeminfo', 'wmic', 'ver', 'powershell',
                'sc', 'net', 'reg', 'tasklist', 'schtasks',
                'gpresult', 'whoami', 'hostname'
            }
            
            if base_cmd in system_commands:
                print("DEBUG: Processing as system command")
                return await self._run_system_cmd(converted_command)
                
            # Handle network commands
            if base_cmd in ['ping', 'ipconfig', 'netstat', 'tracert', 'nslookup']:
                print("DEBUG: Processing as network command")
                return await self._run_network_command(converted_command)
                
            # Handle web/download commands
            if base_cmd in ['curl', 'wget', 'certutil']:
                print("DEBUG: Processing as web command")
                return await self._run_web_command(converted_command)

            print("DEBUG: Processing as regular command")
            return await self._run_regular_command(converted_command)
            
        except Exception as e:
            error_msg = f"BASH TOOL ERROR: Failed to execute command '{command}'\nError: {str(e)}\nType: {type(e).__name__}"
            print(f"DEBUG: {error_msg}")
            return 1, error_msg, str(e)

    async def _run_regular_command(self, command: str) -> tuple[int, str, str]:
        """Handle regular commands with proper error reporting."""
        try:
            cwd = os.getcwd()
            print(f"DEBUG: Current working directory: {cwd}")
            
            # Get base command for routing
            base_cmd = command.split()[0].lower()
            
            # Check for cd commands and return helpful message
            if base_cmd in ['cd', 'chdir', 'pwd']:
                return 1, """Please don't use 'cd' or 'pwd' commands. Instead, use absolute paths in your commands.

                            For example:
                            - Instead of: cd "C:\\Users\\ahmad\\Downloads" && dir
                            - Use: dir "C:\\Users\\ahmad\\Downloads"

                            - Instead of: cd "C:\\path" && mkdir newfolder  
                            - Use: mkdir "C:\\path\\newfolder"

                            This approach is more reliable and doesn't require changing directories.""", ""
            
            # Define command mappings with their Windows equivalents
            simple_commands = {
                # Basic file and directory operations
                'dir': 'dir',
                # cd and pwd commands are blocked - see check above
                'type': lambda x: f'type "{x}"',
                'copy': lambda x, y: f'copy "{x}" "{y}"',
                'move': lambda x, y: f'move "{x}" "{y}"',
                'del': lambda x: f'del "{x}"',
                'erase': lambda x: f'del "{x}"',  # alias for del
                'ren': lambda x, y: f'ren "{x}" "{y}"',
                'rename': lambda x, y: f'ren "{x}" "{y}"',  # alias for ren
                'echo': lambda x: f'echo {x}',
                
                # Directory management
                'tree': 'tree',  # show directory structure
                # chdir is blocked - see check above
                'rd': lambda x: f'rd "{x}"',  # alias for rmdir
                
                # File management
                'comp': lambda x, y: f'comp "{x}" "{y}"',  # compare two files
                'fc': lambda x, y: f'fc "{x}" "{y}"',      # file compare
                'find': lambda x: f'find "{x}"',           # find text in files
                'findstr': lambda x: f'findstr "{x}"',     # find strings in files
                'attrib': lambda x: f'attrib "{x}"',       # display/change file attributes
                
                # System information
                'ver': 'ver',          # display Windows version
                'vol': 'vol',          # display volume label
                'systeminfo': 'systeminfo',  # detailed system information
                'tasklist': 'tasklist',     # list running processes
                'where': lambda x: f'where "{x}"',  # locate programs
                'whoami': 'whoami',     # display current user
                
                # Network commands
                'ipconfig': 'ipconfig',  # display network configuration
                'netstat': 'netstat',    # display network statistics
                'ping': lambda x: f'ping {x}',  # test network connection
                'hostname': 'hostname',  # display computer name
                
                # Time and date
                'time': 'time /t',     # display current time
                'date': 'date /t',     # display current date
                
                # File system
                'chkdsk': lambda x='': f'chkdsk {x}',  # check disk
                'compact': lambda x: f'compact "{x}"',  # compress files
                'fsutil': lambda x: f'fsutil {x}',      # file system utility
                
                # Text processing
                'sort': lambda x: f'sort "{x}"',    # sort text
                'more': lambda x: f'more "{x}"',    # display output one screen at a time
                'clip': lambda x: f'clip < "{x}"',  # copy to clipboard
                
                # Batch file commands
                'call': lambda x: f'call "{x}"',    # call another batch file
                'title': lambda x: f'title {x}',    # set window title
                
                # Environment
                'set': lambda x: f'set {x}',        # display/set environment variables
                'path': 'path',                     # display/set PATH
                
                # Special commands
                'cls': 'cls',          # clear screen
                'exit': 'exit',        # exit command prompt
                'help': lambda x='': f'help {x}',  # get help on commands
                'prompt': lambda x: f'prompt {x}',  # change command prompt
                
                # Power management
                'shutdown': lambda x='/s': f'shutdown {x}',  # shutdown computer
                'powercfg': lambda x: f'powercfg {x}',      # power configuration
                
                # Security and permissions
                'cacls': lambda x: f'cacls "{x}"',    # display/edit file ACLs
                'icacls': lambda x: f'icacls "{x}"',  # improved cacls
                
                # Disk management
                'diskpart': 'diskpart',  # disk partitioning
                'defrag': lambda x: f'defrag "{x}"',  # defragment disk
                
                # Service management
                'sc': lambda x: f'sc {x}',  # service control
                'net': lambda x: f'net {x}',  # network services and resources
                
                # Web and download tools
                'curl': lambda x: f'curl {x}',  # HTTP client
                'wget': lambda x: f'wget {x}',  # Download tool
                'certutil': lambda x: f'certutil {x}',  # Certificate utility (can download files)
            }
            
            if base_cmd in simple_commands:
                print(f"DEBUG: Command '{base_cmd}' found in simple_commands")
                try:
                    # Get all arguments after the command
                    args = command.split(None, 1)[1] if len(command.split()) > 1 else ''
                    print(f"DEBUG: Command arguments: '{args}'")
                    
                    # Handle different command types
                    if callable(simple_commands[base_cmd]):
                        if base_cmd in ['copy', 'move', 'ren', 'rename', 'comp', 'fc']:
                            # Commands that require exactly two arguments
                            try:
                                src, dst = args.rsplit(None, 1)
                                cmd = simple_commands[base_cmd](src.strip('"'), dst.strip('"'))
                            except ValueError:
                                return 1, f"Error: {base_cmd} command requires two arguments (source and destination)", ""
                        
                        elif base_cmd in ['sc', 'net', 'fsutil', 'powercfg']:
                            # Commands that pass through arguments unchanged
                            cmd = simple_commands[base_cmd](args)
                        
                        elif base_cmd == 'ping':
                            # Special handling for ping command
                            # Strip any quotes and ensure only 4 pings by default
                            target = args.strip().strip('"')
                            if not any(switch in args.lower() for switch in ['-n', '/n']):
                                target = f"-n 4 {target}"  # Add default count if not specified
                            cmd = f"ping {target}"
                        
                        elif base_cmd in ['find', 'findstr']:
                            # Search commands need special handling for multiple arguments
                            cmd = simple_commands[base_cmd](args.replace('"', '""'))
                        
                        elif base_cmd in ['help', 'chkdsk']:
                            # Commands that work with or without arguments
                            cmd = simple_commands[base_cmd](args) if args else simple_commands[base_cmd]()
                        
                        else:
                            # Default single argument handling
                            cmd = simple_commands[base_cmd](args.strip('"'))
                    else:
                        # Commands that don't need argument processing
                        if base_cmd == 'dir' and args:
                            # dir command with arguments (like directory path)
                            cmd = f'dir {args}'
                        else:
                            cmd = simple_commands[base_cmd]
                        
                    # Add any common switches for better output
                    if base_cmd == 'find':
                        cmd += ' /N'  # Add line numbers
                    elif base_cmd == 'tree':
                        cmd += ' /F'  # Show files in addition to directories
                    elif base_cmd in ['tasklist', 'netstat']:
                        cmd += ' /FO TABLE'  # Format as table
                        
                    print(f"DEBUG: Final command to execute: {cmd}")
                        
                except Exception as e:
                    error_msg = f"Error processing {base_cmd} command: {str(e)}"
                    print(f"DEBUG: {error_msg}")
                    return 1, error_msg, ""
                
                # Execute the command
                full_cmd = f'cmd /c {cmd}'
                print(f"DEBUG: Executing: {full_cmd}")
                
                try:
                    process = await asyncio.create_subprocess_shell(
                        full_cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                        shell=True,
                        cwd=cwd
                    )
                    stdout, stderr = await process.communicate()
                    
                    # Decode output
                    try:
                        output = stdout.decode('utf-8') if stdout else ''
                    except UnicodeDecodeError:
                        output = stdout.decode('cp1252', errors='ignore') if stdout else ''
                    
                    try:
                        error = stderr.decode('utf-8') if stderr else ''
                    except UnicodeDecodeError:
                        error = stderr.decode('cp1252', errors='ignore') if stderr else ''
                    
                    print(f"DEBUG: Command completed with return code: {process.returncode}")
                    print(f"DEBUG: Output length: {len(output)} characters")
                    print(f"DEBUG: Error length: {len(error)} characters")
                    
                    if process.returncode == 0:
                        return 0, output or f"Successfully executed {base_cmd} command", error
                    else:
                        error_msg = f"Command '{cmd}' failed with return code {process.returncode}\nOutput: {output}\nError: {error}"
                        return process.returncode, error_msg, error
                        
                except Exception as e:
                    error_msg = f"Failed to execute command '{full_cmd}': {str(e)}"
                    print(f"DEBUG: Execution error: {error_msg}")
                    return 1, error_msg, ""

            # Special handling for directory creation
            if command.lower().startswith(('md ', 'mkdir ')):
                print("DEBUG: Processing mkdir command")
                try:
                    # Extract directory name
                    dir_name = command.split('"')[1] if '"' in command else command.split(' ', 1)[1]
                    print(f"DEBUG: Creating directory: {dir_name}")
                    # Create directory directly using Python
                    os.makedirs(dir_name, exist_ok=True)
                    return 0, f"Successfully created directory: {dir_name}", ""
                except Exception as dir_e:
                    error_msg = f"Failed to create directory: {str(dir_e)}"
                    print(f"DEBUG: {error_msg}")
                    return 1, error_msg, ""
            
            # Special handling for directory removal
            elif command.lower().startswith(('rmdir ', 'rd ')):
                print("DEBUG: Processing rmdir command")
                try:
                    # Parse command
                    parts = command.split()
                    force_remove = '/s' in parts
                    # Get directory name (handling quotes)
                    if '"' in command:
                        dir_name = command.split('"')[1]
                    else:
                        dir_name = next(part for part in parts[1:] if not part.startswith('/'))
                    
                    print(f"DEBUG: Removing directory: {dir_name}, force: {force_remove}")
                    
                    if force_remove:
                        import shutil
                        shutil.rmtree(dir_name)
                    else:
                        os.rmdir(dir_name)
                    return 0, f"Successfully removed directory: {dir_name}", ""
                except FileNotFoundError:
                    return 1, f"Directory not found: {dir_name}", ""
                except OSError as e:
                    if e.errno == 39 or "directory not empty" in str(e).lower():
                        return 1, f"Directory not empty: {dir_name}. Use 'rmdir /s {dir_name}' to remove directory and its contents.", ""
                    return 1, f"Failed to remove directory: {str(e)}", ""
            
            # For other commands, run them directly with cmd
            print("DEBUG: Running command directly with cmd")
            full_cmd = f'cmd /c {command}'
            print(f"DEBUG: Direct execution: {full_cmd}")
            
            process = await asyncio.create_subprocess_shell(
                full_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW,
                shell=True,
                cwd=cwd
            )

            stdout, stderr = await process.communicate()
            
            try:
                stdout_str = stdout.decode('utf-8') if stdout else ''
                stderr_str = stderr.decode('utf-8') if stderr else ''
            except UnicodeDecodeError:
                stdout_str = stdout.decode('cp1252', errors='ignore') if stdout else ''
                stderr_str = stderr.decode('cp1252', errors='ignore') if stderr else ''

            print(f"DEBUG: Direct command completed with return code: {process.returncode}")
            
            if process.returncode == 0:
                return 0, stdout_str or "Command executed successfully", stderr_str
            else:
                error_msg = f"Command '{command}' failed with return code {process.returncode}\nOutput: {stdout_str}\nError: {stderr_str}"
                return process.returncode, error_msg, stderr_str

        except Exception as e:
            error_msg = f"REGULAR COMMAND ERROR: Failed to execute '{command}'\nError: {str(e)}\nType: {type(e).__name__}"
            print(f"DEBUG: {error_msg}")
            return 1, error_msg, str(e)

    def _convert_unix_to_windows(self, command: str) -> str:
        """Convert Unix-style commands and paths to Windows equivalents."""
        # Don't modify URLs in the command
        if 'http://' in command or 'https://' in command:
            # Only convert ~ to home directory, leave URLs alone
            if '~' in command:
                home_dir = os.path.expanduser('~')
                # Be more careful about ~ replacement near URLs
                import re
                # Replace ~ only when it's clearly a path (not part of URL)
                command = re.sub(r'(?<!://[^/]*?)~(?=/)', f'"{home_dir}"', command)
                command = re.sub(r'^~(?=/)', f'"{home_dir}"', command)
                command = re.sub(r'\s~(?=/)', f' "{home_dir}"', command)
            return command
        
        # Convert ~ to user home directory
        if '~' in command:
            home_dir = os.path.expanduser('~')
            command = command.replace('~/', f'"{home_dir}\\').replace('~', f'"{home_dir}"')
        
        # Convert forward slashes to backslashes in paths
        # Be careful not to convert URLs or command switches
        import re
        # Look for path-like patterns and convert them
        command = re.sub(r'(?<!/)/(?!/)', '\\\\', command)
        
        return command

    async def _run_compound_command(self, command: str) -> tuple[int, str, str]:
        """Handle compound commands with && or || operators."""
        try:
            print(f"DEBUG: Processing compound command: {command}")
            
            # Split on && or || but preserve the operator
            if '&&' in command:
                parts = command.split('&&')
                operator = '&&'
            else:
                parts = command.split('||')
                operator = '||'
            
            print(f"DEBUG: Split into {len(parts)} parts using '{operator}' operator")
            for i, part in enumerate(parts):
                print(f"DEBUG: Part {i+1}: '{part.strip()}'")
            
            all_output = []
            last_returncode = 0
            
            for i, part in enumerate(parts):
                part = part.strip()
                if not part:
                    print(f"DEBUG: Skipping empty part {i+1}")
                    continue
                
                print(f"DEBUG: Executing part {i+1}: '{part}'")
                
                # Run each part
                returncode, stdout, stderr = await self.run(part, _skip_compound=True)
                
                print(f"DEBUG: Part {i+1} completed with return code: {returncode}")
                print(f"DEBUG: Part {i+1} output length: {len(stdout) if stdout else 0}")
                print(f"DEBUG: Part {i+1} error length: {len(stderr) if stderr else 0}")
                
                if stdout:
                    all_output.append(stdout)
                
                # Handle operator logic
                if operator == '&&' and returncode != 0:
                    # With &&, stop on first failure
                    error_msg = stderr if stderr else f"Command failed: {part}"
                    print(f"DEBUG: Stopping && chain due to failure in part {i+1}")
                    return returncode, '\n'.join(all_output), error_msg
                elif operator == '||' and returncode == 0:
                    # With ||, stop on first success
                    print(f"DEBUG: Stopping || chain due to success in part {i+1}")
                    return 0, '\n'.join(all_output), ""
                
                last_returncode = returncode
            
            final_output = '\n'.join(all_output)
            print(f"DEBUG: Compound command completed with final return code: {last_returncode}")
            print(f"DEBUG: Final output length: {len(final_output)}")
            
            return last_returncode, final_output, ""

        except Exception as e:
            error_msg = f"COMPOUND COMMAND ERROR: Failed to execute '{command}'\nError: {str(e)}\nType: {type(e).__name__}"
            print(f"DEBUG: {error_msg}")
            return 1, error_msg, str(e)

    async def stop(self):
        """Stop the shell process."""
        if self._process is not None:
            try:
                self._process.terminate()
                await self._process.wait()
            except ProcessLookupError:
                pass
            self._process = None


class BashTool(BaseAnthropicTool):
    """
    A tool that allows the agent to run commands in a Windows command shell.
    The tool parameters are defined by Anthropic and are not editable.
    """

    name: Literal["bash"] = "bash"
    api_type: Literal["bash_20250124"] = "bash_20250124"
    _session: AsyncWindowsShell

    def __init__(self):
        super().__init__()
        self._session = AsyncWindowsShell()
    
    def to_params(self) -> BetaToolParam:
        """Convert this tool to its API parameters."""
        return {"name": self.name, "type": self.api_type}

    async def __call__(
        self,
        *,
        command: str | None = None,
        restart: bool | None = None,
        **kwargs: Any,
    ) -> ToolResult:
        """Run a command in the Windows command shell."""
        if restart:
            await self._session.stop()
            return ToolResult()

        if not command:
            raise ToolError("command is required")

        returncode, stdout, stderr = await self._session.run(command)
        
        if returncode != 0:
            if stderr:
                return ToolResult(error=stderr)
            else:
                return ToolResult(error=stdout if stdout else "Command failed")

        return ToolResult(output=stdout.strip() if stdout else "Command executed successfully")