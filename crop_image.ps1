
$sourceCode = @"
using System;
using System.Drawing;
using System.Drawing.Imaging;
using System.IO;

public class ImageProcessor
{
    public static string CropBlackBorders(string inputPath, int threshold = 15)
    {
        if (!File.Exists(inputPath)) return "File not found";

        try
        {
            using (Bitmap original = new Bitmap(inputPath))
            {
                int width = original.Width;
                int height = original.Height;
                
                int top = 0;
                int bottom = height - 1;
                int left = 0;
                int right = width - 1;

                // Lock bits for speed
                BitmapData data = original.LockBits(new Rectangle(0, 0, width, height), ImageLockMode.ReadOnly, PixelFormat.Format24bppRgb);
                int stride = data.Stride;
                
                unsafe
                {
                    byte* ptr = (byte*)data.Scan0;
                    
                    // Find Top
                    bool stop = false;
                    for (int y = 0; y < height; y++)
                    {
                        for (int x = 0; x < width; x++)
                        {
                            int idx = y * stride + x * 3;
                            byte b = ptr[idx];
                            byte g = ptr[idx + 1];
                            byte r = ptr[idx + 2];
                            
                            if (r > threshold || g > threshold || b > threshold)
                            {
                                top = y;
                                stop = true;
                                break;
                            }
                        }
                        if (stop) break;
                    }
                    
                    // Find Bottom
                    stop = false;
                    for (int y = height - 1; y >= top; y--)
                    {
                        for (int x = 0; x < width; x++)
                        {
                            int idx = y * stride + x * 3;
                            byte b = ptr[idx];
                            byte g = ptr[idx + 1];
                            byte r = ptr[idx + 2];
                            
                            if (r > threshold || g > threshold || b > threshold)
                            {
                                bottom = y;
                                stop = true;
                                break;
                            }
                        }
                        if (stop) break;
                    }
                    
                    // Find Left
                    stop = false;
                    for (int x = 0; x < width; x++)
                    {
                        for (int y = top; y <= bottom; y++)
                        {
                            int idx = y * stride + x * 3;
                            byte b = ptr[idx];
                            byte g = ptr[idx + 1];
                            byte r = ptr[idx + 2];
                            
                            if (r > threshold || g > threshold || b > threshold)
                            {
                                left = x;
                                stop = true;
                                break;
                            }
                        }
                        if (stop) break;
                    }
                    
                    // Find Right
                    stop = false;
                    for (int x = width - 1; x >= left; x--)
                    {
                        for (int y = top; y <= bottom; y++)
                        {
                            int idx = y * stride + x * 3;
                            byte b = ptr[idx];
                            byte g = ptr[idx + 1];
                            byte r = ptr[idx + 2];
                            
                            if (r > threshold || g > threshold || b > threshold)
                            {
                                right = x;
                                stop = true;
                                break;
                            }
                        }
                        if (stop) break;
                    }
                }
                
                original.UnlockBits(data);

                if (left > right || top > bottom)
                {
                    // Image is completely black?
                    return "Image is fully black or below threshold";
                }
                
                // Check if crop is needed
                if (left == 0 && top == 0 && right == width - 1 && bottom == height - 1)
                {
                     return "No cropping needed";
                }

                int cropWidth = right - left + 1;
                int cropHeight = bottom - top + 1;

                using (Bitmap cropped = new Bitmap(cropWidth, cropHeight))
                {
                    using (Graphics g = Graphics.FromImage(cropped))
                    {
                        g.DrawImage(original, new Rectangle(0, 0, cropWidth, cropHeight), new Rectangle(left, top, cropWidth, cropHeight), GraphicsUnit.Pixel);
                    }
                    
                    // Save to temp file
                    string tempPath = inputPath + ".temp.jpg";
                    cropped.Save(tempPath, ImageFormat.Jpeg);
                }
            }
            
            // Replace original
            File.Delete(inputPath);
            File.Move(inputPath + ".temp.jpg", inputPath);
            
            return "Success";
        }
        catch (Exception ex)
        {
            return "Error: " + ex.ToString();
        }
    }
}
"@

Add-Type -TypeDefinition $sourceCode -ReferencedAssemblies System.Drawing

$targetFile = Resolve-Path "flyer_20260223.jpg"
Write-Host "Processing $targetFile..."
$result = [ImageProcessor]::CropBlackBorders($targetFile.Path, 20)
Write-Host "Result: $result"
