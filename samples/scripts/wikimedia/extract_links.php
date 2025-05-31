#!/usr/bin/env php
<?php
// Optimized version using numeric IDs for keys

$valid_ext = '/\.(jpg|jpeg|jpe|jp2|jpx|dng|heic|heif|avif|webp|cr2|cr3|nef|arw|orf|rw2|raf|srw|pef|tif|tiff)$/i';
$seen = [];
$count = 0;
$empty_count = 0;
$skipped_ext = 0;
$min_count = 50;
$max_field_length = 50; // Skip fields with names longer than this

// Blacklist of fields to ignore
$field_blacklist = [
    'MEDIAWIKI_EXIF_VERSION' => true,
];

// Map field names to numeric IDs
$field_to_id = [];
$field_count = []; // Track how many times each field appears
$make_model_count = []; // Track Make/Model combinations
$software_count = []; // Track Software values
$next_id = 0;
$skipped_long_fields = 0;
$skipped_blacklisted = 0;
$error_count = 0;

// Open debug file for keys
$debug = fopen('debug_keys.txt', 'w');

// Function to create safe filesystem names
function make_safe_filename($str, $max_length = 100) {
    // Replace unsafe chars with underscore
    $safe = preg_replace('/[^a-zA-Z0-9._-]/', '_', $str);
    // Remove multiple underscores
    $safe = preg_replace('/_+/', '_', $safe);
    // Trim underscores and spaces
    $safe = trim($safe, '_ ');
    // Limit length
    if (strlen($safe) > $max_length) {
        $safe = substr($safe, 0, $max_length);
    }
    return $safe;
}

// Function to create error key
function create_error_key($filename, $error_count) {
    $file_base = pathinfo($filename, PATHINFO_FILENAME);
    $safe_base = make_safe_filename($file_base);
    return "errors/$safe_base.error.$error_count";
}

// Function to create software key
function create_software_key($software_tags) {
    $combined = implode(' ', $software_tags);
    $safe_software = make_safe_filename($combined);
    return "software/$safe_software";
}

// Function to create device key
function create_device_key($make, $model) {
    $safe_make = make_safe_filename($make, 50);
    $safe_model = make_safe_filename($model, 50);
    
    if ($safe_make && $safe_model) {
        return "device/$safe_make/$safe_model";
    } elseif ($safe_make) {
        return "device/$safe_make/unknown";
    } elseif ($safe_model) {
        return "device/unknown/$safe_model";
    }
    return "device/unknown/unknown";
}

// Function to create tags key
function create_tags_key($keys, $field_blacklist) {
    // Filter out blacklisted tags
    $filtered_keys = [];
    foreach ($keys as $key) {
        if (!isset($field_blacklist[$key])) {
            $filtered_keys[] = $key;
        }
    }
    
    if (empty($filtered_keys)) {
        return "tags/empty";
    }
    
    $tag_list = implode('.', $filtered_keys);
    $safe_tags = make_safe_filename($tag_list);
    
    // If too long, truncate and add hash
    if (strlen($safe_tags) > 64) {
        $safe_tags = substr($safe_tags, 0, 64) . '_' . substr(md5($tag_list), 0, 8);
    }
    
    return "tags/$safe_tags";
}

// Function to write stats files
function write_stats_files() {
    global $make_model_count, $software_count;
    
    // Count individual makes and models
    $make_count = [];
    $model_count = [];
    
    foreach ($make_model_count as $make_model => $count) {
        $parts = explode(' / ', $make_model);
        $make = trim($parts[0]);
        $model = isset($parts[1]) ? trim($parts[1]) : '';
        
        if ($make) {
            if (!isset($make_count[$make])) $make_count[$make] = 0;
            $make_count[$make] += $count;
        }
        
        if ($model) {
            if (!isset($model_count[$model])) $model_count[$model] = 0;
            $model_count[$model] += $count;
        }
    }
    
    // Sort and write makes
    arsort($make_count);
    $make_output = '';
    foreach ($make_count as $make => $count) {
        $make_output .= "$count\t$make\n";
    }
    file_put_contents('makes.txt', $make_output);
    
    // Sort and write models
    arsort($model_count);
    $model_output = '';
    foreach ($model_count as $model => $count) {
        $model_output .= "$count\t$model\n";
    }
    file_put_contents('models.txt', $model_output);
    
    // Sort and write software
    arsort($software_count);
    $software_output = '';
    foreach ($software_count as $software => $count) {
        $software_output .= "$count\t$software\n";
    }
    file_put_contents('software.txt', $software_output);
}

// Function to print summary
function print_summary() {
    global $count, $skipped_ext, $empty_count, $skipped_blacklisted, $skipped_long_fields;
    global $seen, $min_count, $field_to_id, $software_count, $error_count;
    
    // Write stats files
    write_stats_files();
    
    // Count how many met the threshold
    $output_count = 0;
    foreach ($seen as $data) {
        if ($data['count'] >= $min_count) $output_count++;
    }
    
    fwrite(STDERR, "\n\nSUMMARY:\n");
    fwrite(STDERR, "Total records: $count\n");
    fwrite(STDERR, "Skipped (wrong extension): $skipped_ext\n");
    fwrite(STDERR, "Empty metadata: $empty_count\n");
    fwrite(STDERR, "Error cases found: $error_count\n");
    fwrite(STDERR, "Skipped blacklisted fields: $skipped_blacklisted\n");
    fwrite(STDERR, "Skipped long field names: $skipped_long_fields\n");
    fwrite(STDERR, "Unique EXIF producers: " . count($seen) . "\n");
    fwrite(STDERR, "Producers with >= $min_count examples: $output_count\n");
    fwrite(STDERR, "Total unique field names seen: " . count($field_to_id) . "\n");
    
    // Sort Software by popularity
    arsort($software_count);
    fwrite(STDERR, "\nTop 100 Software values by popularity:\n");
    $i = 0;
    foreach ($software_count as $software => $software_count_val) {
        fwrite(STDERR, sprintf("%4d. %-50s %d\n", ++$i, $software, $software_count_val));
        if ($i >= 100) break;
    }
    
    // Write all unique field names to file for PII analysis
    $field_list = array_keys($field_to_id);
    sort($field_list);
    file_put_contents('all_fields.txt', implode("\n", $field_list) . "\n");
    fwrite(STDERR, "\nWrote " . count($field_list) . " unique field names to all_fields.txt\n");
}

// Register signal handler for Ctrl+C
pcntl_signal(SIGINT, function($signo) {
    print_summary();
    exit(0);
});

while ($line = fgets(STDIN)) {
    if (strpos($line, 'INSERT INTO `image` VALUES') !== 0) continue;
    
    // Remove the INSERT prefix and split by record boundaries
    $line = substr($line, 27); // Remove "INSERT INTO `image` VALUES ("
    $line = rtrim($line, ");\n\r");
    $records = explode('),(', $line);
    
    foreach ($records as $record) {
        $count++;
        
        // Quick regex to extract just filename and metadata fields
        if (!preg_match("/^'([^']*)',[^,]*,[^,]*,[^,]*,'([^'\\\\]*(?:\\\\.[^'\\\\]*)*)'/", $record, $match)) continue;
        
        $filename = stripslashes($match[1]);
        $metadata = $match[2];
        
        // Check extension
        if (!preg_match($valid_ext, $filename)) {
            $skipped_ext++;
            continue;
        }
        
        // Unescape metadata - stripslashes handles \', \", \\, \n, \r, \0
        $metadata = stripslashes($metadata);
        
        $field_ids = [];
        $keys = null;
        
        $exif_data = null;
        
        $has_error = false;
        
        // Try JSON first
        if ($metadata && $metadata[0] === '{') {
            $data = @json_decode($metadata, true);
            if ($data && isset($data['data'])) {
                // Check for errors
                if (isset($data['data']['_error']) || isset($data['data']['errors'])) {
                    $has_error = true;
                }
                
                // If exif field exists, use only that
                if (isset($data['data']['exif']) && is_array($data['data']['exif'])) {
                    $exif_data = $data['data']['exif'];
                    $keys = array_keys($exif_data);
                } else {
                    $exif_data = $data['data'];
                    $keys = array_keys($exif_data);
                }
            }
        } 
        // Try PHP serialized
        elseif ($metadata && $metadata[0] === 'a') {
            $data = @unserialize($metadata);
            if ($data && is_array($data)) {
                // Check for errors
                if (isset($data['_error']) || isset($data['errors'])) {
                    $has_error = true;
                }
                
                // If exif field exists, use only that
                if (isset($data['exif']) && is_array($data['exif'])) {
                    $exif_data = $data['exif'];
                    $keys = array_keys($exif_data);
                } else {
                    $exif_data = $data;
                    $keys = array_keys($exif_data);
                }
            }
        }
        
        // Track Make/Model combinations and determine EXIF producer key
        $exif_producer_key = '';
        
        if ($exif_data) {
            $make = isset($exif_data['Make']) ? $exif_data['Make'] : '';
            $model = isset($exif_data['Model']) ? $exif_data['Model'] : '';
            
            if ($make || $model) {
                $make_model = trim($make . ' / ' . $model);
                if (!isset($make_model_count[$make_model])) {
                    $make_model_count[$make_model] = 0;
                }
                $make_model_count[$make_model]++;
            }
            
            // Track Software
            if (isset($exif_data['Software']) && $exif_data['Software']) {
                $software = is_array($exif_data['Software']) ? 
                    json_encode($exif_data['Software']) : 
                    (string)$exif_data['Software'];
                if (!isset($software_count[$software])) {
                    $software_count[$software] = 0;
                }
                $software_count[$software]++;
            }
            
            // Determine EXIF producer key with hierarchy
            // 1) Software tag first (plus other software markers)
            $software_tags = [];
            if (isset($exif_data['Software']) && $exif_data['Software']) {
                $software_tags[] = is_array($exif_data['Software']) ? 
                    json_encode($exif_data['Software']) : 
                    (string)$exif_data['Software'];
            }
            // Tags identifying the software that created the exif data
            if (isset($exif_data['ProcessingSoftware']) && $exif_data['ProcessingSoftware']) {
                $software_tags[] = is_array($exif_data['ProcessingSoftware']) ? 
                    json_encode($exif_data['ProcessingSoftware']) : 
                    (string)$exif_data['ProcessingSoftware'];
            }
            
            // Get file extension in lowercase
            $file_ext = strtolower(pathinfo($filename, PATHINFO_EXTENSION));
            
            // Create appropriate key based on data type
            if ($has_error) {
                $error_count++;
                $exif_producer_key = create_error_key($filename, $error_count);
            }
            elseif ($software_tags) {
                $exif_producer_key = create_software_key($software_tags);
            }
            elseif ($make || $model) {
                $exif_producer_key = create_device_key($make, $model);
            }
            else {
                $exif_producer_key = create_tags_key($keys, $field_blacklist);
            }
            
            // Add file extension
            $exif_producer_key = "$exif_producer_key.$file_ext";
        }
        
        // Process keys if we got any
        if ($keys) {
            foreach ($keys as $key) {
                // Skip blacklisted fields
                if (isset($field_blacklist[$key])) {
                    $skipped_blacklisted++;
                    continue;
                }
                
                // Skip fields with overly long names
                if (strlen($key) > $max_field_length) {
                    $skipped_long_fields++;
                    continue;
                }
                
                if (!isset($field_to_id[$key])) {
                    $field_to_id[$key] = $next_id++;
                    $field_count[$key] = 0;
                }
                $field_count[$key]++;
                $field_ids[] = $field_to_id[$key];
            }
        }
        
        if ($field_ids || $exif_producer_key) {
            // Use the full producer key as the identifier
            $hash = $exif_producer_key ? $exif_producer_key : 'tags/unknown_' . md5(serialize($field_ids));
            
            if (!isset($seen[$hash])) {
                $seen[$hash] = ['count' => 0, 'filename' => $filename, 'producer_key' => $exif_producer_key, 'field_ids' => $field_ids];
            }
            $seen[$hash]['count']++;
            
            // Output URL at powers of 2 for unbiased sampling (or always for errors)
            $count_val = $seen[$hash]['count'];
            $is_error = strpos($hash, 'errors/') === 0;
            
            if ($is_error || ($count_val > 0 && ($count_val & ($count_val - 1)) == 0)) {
                // Use 9999999 as count for error files
                $output_count = $is_error ? 9999999 : $count_val;
                // Calculate MD5 of filename for upload path
                $md5 = md5($seen[$hash]['filename']);
                $dir1 = substr($md5, 0, 1);
                $dir2 = substr($md5, 0, 2);
                
                echo "$hash\t$output_count\thttps://upload.wikimedia.org/wikipedia/commons/$dir1/$dir2/" . urlencode($seen[$hash]['filename']) . "\n";
                
                // Write producer key or field names to debug file
                if ($seen[$hash]['producer_key']) {
                    fwrite($debug, $seen[$hash]['producer_key'] . "\n");
                } else {
                    $field_names = [];
                    foreach ($seen[$hash]['field_ids'] as $id) {
                        $field_names[] = array_search($id, $field_to_id);
                    }
                    fwrite($debug, 'TAGS:' . implode(', ', $field_names) . "\n");
                }
            }
        } else {
            $empty_count++;
        }
        
        if ($count % 50000 == 0) {
            fwrite(STDERR, "Processed: $count | Unique producers: " . count($seen) . " | Unique field names: " . count($field_to_id) . "\n");
        }
        
        // Handle signals
        pcntl_signal_dispatch();
    }
}

// Print final summary
print_summary();

fclose($debug);
?>
