"use client";

import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  Target, 
  FileText, 
  Upload, 
  Brain,
  Loader2,
  CheckCircle,
  AlertCircle
} from 'lucide-react';

import CoordinateGradingView from './coordinate-grading-view';
import CroppedRegionGradingView from './cropped-region-grading-view';

interface EnhancedGradingResult {
  submission_id: string;
  display_mode: string;
  grading_summary: {
    score: number;
    max_score: number;
    percentage: number;
    feedback: string;
    strengths: string[];
    suggestions: string[];
  };
  coordinate_annotations?: Array<{
    annotation_id: string;
    coordinates: { x: number; y: number; w: number; h: number };
    error_details: {
      type: string;
      description: string;
      correct_answer: string;
      severity: string;
    };
    knowledge_points: string[];
    popup_content: {
      title: string;
      description: string;
      correct_solution: string;
      knowledge_links: string[];
    };
  }>;
  error_cards?: Array<{
    card_id: string;
    error_details: {
      type: string;
      description: string;
      correct_answer: string;
      severity: string;
    };
    cropped_image: {
      file_id: string;
      url: string;
      coordinates: { x: number; y: number; w: number; h: number };
    };
    knowledge_points: string[];
    actions: {
      locate_in_original: {
        coordinates: { x: number; y: number; w: number; h: number };
        description: string;
      };
      view_explanation: {
        detailed_analysis: string;
        solution_steps: string;
      };
      related_practice: {
        knowledge_points: string[];
        difficulty_level: string;
      };
    };
  }>;
  original_image_url?: string;
  knowledge_point_summary: {
    total_points: number;
    points: string[];
    mastery_analysis: any;
  };
  processing_timestamp: string;
}

interface EnhancedAIGradingSystemProps {
  onGradingComplete?: (result: EnhancedGradingResult) => void;
  defaultDisplayMode?: 'coordinates' | 'cropped_regions';
}

export default function EnhancedAIGradingSystem({
  onGradingComplete,
  defaultDisplayMode = 'coordinates'
}: EnhancedAIGradingSystemProps) {
  const [currentStep, setCurrentStep] = useState<'upload' | 'grading' | 'results'>('upload');
  const [gradingResult, setGradingResult] = useState<EnhancedGradingResult | null>(null);
  const [displayMode, setDisplayMode] = useState<'coordinates' | 'cropped_regions'>(defaultDisplayMode);
  const [isGrading, setIsGrading] = useState(false);
  const [gradingProgress, setGradingProgress] = useState(0);
  
  // Form state
  const [formData, setFormData] = useState({
    questionText: '',
    answerStandard: '',
    gradingInstructions: '',
    submissionId: crypto.randomUUID()
  });
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file && file.type.startsWith('image/')) {
      setUploadedFile(file);
    }
  };

  const handleStartGrading = async () => {
    if (!uploadedFile || !formData.questionText || !formData.answerStandard) {
      return;
    }

    setIsGrading(true);
    setCurrentStep('grading');
    setGradingProgress(0);

    try {
      // Simulate progress
      const progressInterval = setInterval(() => {
        setGradingProgress(prev => {
          const next = prev + Math.random() * 15;
          return next > 90 ? 90 : next;
        });
      }, 500);

      // Prepare form data for API
      const apiFormData = new FormData();
      apiFormData.append('submission_id', formData.submissionId);
      apiFormData.append('question_text', formData.questionText);
      apiFormData.append('answer_standard', formData.answerStandard);
      apiFormData.append('grading_instructions', formData.gradingInstructions || '');
      apiFormData.append('display_mode', displayMode);
      apiFormData.append('image_file', uploadedFile);

      // Call enhanced grading API
      const response = await fetch('/api/v1/enhanced-grading/upload-and-grade', {
        method: 'POST',
        body: apiFormData,
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
        }
      });

      clearInterval(progressInterval);
      setGradingProgress(100);

      if (!response.ok) {
        throw new Error('批改失败');
      }

      const result = await response.json();
      setGradingResult(result);
      setCurrentStep('results');
      
      if (onGradingComplete) {
        onGradingComplete(result);
      }

    } catch (error) {
      console.error('Grading error:', error);
      alert('批改过程中出现错误，请重试');
      setCurrentStep('upload');
    } finally {
      setIsGrading(false);
    }
  };

  const handleSwitchDisplayMode = async (newMode: 'coordinates' | 'cropped_regions') => {
    if (!gradingResult || newMode === displayMode) return;

    setIsGrading(true);
    
    try {
      // Re-grade with new display mode
      const response = await fetch('/api/v1/enhanced-grading/grade-visual', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
        },
        body: JSON.stringify({
          submission_id: gradingResult.submission_id,
          image_file_id: gradingResult.original_image_url?.split('/').pop(),
          question_text: formData.questionText,
          answer_standard: formData.answerStandard,
          grading_instructions: formData.gradingInstructions,
          display_mode: newMode
        })
      });

      if (!response.ok) {
        throw new Error('切换显示模式失败');
      }

      const result = await response.json();
      setGradingResult(result);
      setDisplayMode(newMode);

    } catch (error) {
      console.error('Mode switch error:', error);
      alert('切换显示模式失败，请重试');
    } finally {
      setIsGrading(false);
    }
  };

  const renderUploadStep = () => (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Upload className="w-5 h-5" />
            上传作业和设置批改标准
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Display Mode Selection */}
          <div>
            <label className="block text-sm font-medium mb-2">批改显示模式</label>
            <Tabs value={displayMode} onValueChange={(value) => setDisplayMode(value as any)}>
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="coordinates" className="flex items-center gap-2">
                  <Target className="w-4 h-4" />
                  坐标标注模式
                </TabsTrigger>
                <TabsTrigger value="cropped_regions" className="flex items-center gap-2">
                  <FileText className="w-4 h-4" />
                  局部图卡片模式
                </TabsTrigger>
              </TabsList>
            </Tabs>
            <p className="text-xs text-muted-foreground mt-1">
              {displayMode === 'coordinates' 
                ? '在原图上通过坐标点标注错误，点击查看详情'
                : '将错误区域裁剪为局部图片，配合文字说明展示'
              }
            </p>
          </div>

          {/* File Upload */}
          <div>
            <label className="block text-sm font-medium mb-2">上传作业图片</label>
            <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
              <input
                type="file"
                accept="image/*"
                onChange={handleFileUpload}
                className="hidden"
                id="file-upload"
              />
              <label htmlFor="file-upload" className="cursor-pointer">
                {uploadedFile ? (
                  <div className="space-y-2">
                    <img
                      src={URL.createObjectURL(uploadedFile)}
                      alt="上传的作业"
                      className="max-h-32 mx-auto rounded"
                    />
                    <p className="text-sm font-medium">{uploadedFile.name}</p>
                    <p className="text-xs text-muted-foreground">点击更换图片</p>
                  </div>
                ) : (
                  <div className="space-y-2">
                    <Upload className="w-8 h-8 mx-auto text-gray-400" />
                    <p className="text-sm font-medium">点击上传作业图片</p>
                    <p className="text-xs text-muted-foreground">支持 PNG、JPG 格式</p>
                  </div>
                )}
              </label>
            </div>
          </div>

          {/* Question Text */}
          <div>
            <label className="block text-sm font-medium mb-2">题目内容</label>
            <textarea
              value={formData.questionText}
              onChange={(e) => setFormData(prev => ({ ...prev, questionText: e.target.value }))}
              placeholder="请输入题目的文字内容..."
              className="w-full p-3 border rounded-lg resize-none"
              rows={3}
            />
          </div>

          {/* Answer Standard */}
          <div>
            <label className="block text-sm font-medium mb-2">标准答案</label>
            <textarea
              value={formData.answerStandard}
              onChange={(e) => setFormData(prev => ({ ...prev, answerStandard: e.target.value }))}
              placeholder="请输入标准答案或答题要点..."
              className="w-full p-3 border rounded-lg resize-none"
              rows={3}
            />
          </div>

          {/* Grading Instructions */}
          <div>
            <label className="block text-sm font-medium mb-2">批改要求（可选）</label>
            <textarea
              value={formData.gradingInstructions}
              onChange={(e) => setFormData(prev => ({ ...prev, gradingInstructions: e.target.value }))}
              placeholder="请输入特殊的批改要求，如评分标准、注意事项等..."
              className="w-full p-3 border rounded-lg resize-none"
              rows={2}
            />
          </div>

          <Button
            onClick={handleStartGrading}
            disabled={!uploadedFile || !formData.questionText || !formData.answerStandard}
            className="w-full"
            size="lg"
          >
            <Brain className="w-5 h-5 mr-2" />
            开始AI智能批改
          </Button>
        </CardContent>
      </Card>
    </div>
  );

  const renderGradingStep = () => (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Brain className="w-6 h-6 text-primary animate-pulse" />
          AI正在智能批改中...
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span>批改进度</span>
            <span>{Math.round(gradingProgress)}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div 
              className="bg-primary h-2 rounded-full transition-all duration-500"
              style={{ width: `${gradingProgress}%` }}
            />
          </div>
        </div>
        
        <div className="text-center text-sm text-muted-foreground">
          {gradingProgress < 20 && "正在分析题目结构..."}
          {gradingProgress >= 20 && gradingProgress < 40 && "正在识别学生答案..."}
          {gradingProgress >= 40 && gradingProgress < 60 && "正在对比标准答案..."}
          {gradingProgress >= 60 && gradingProgress < 80 && "正在生成坐标标注..."}
          {gradingProgress >= 80 && gradingProgress < 100 && "正在完善批改报告..."}
          {gradingProgress === 100 && "批改完成！"}
        </div>

        {isGrading && (
          <div className="flex justify-center">
            <Loader2 className="w-6 h-6 animate-spin text-primary" />
          </div>
        )}
      </CardContent>
    </Card>
  );

  const renderResultsStep = () => {
    if (!gradingResult) return null;

    return (
      <div className="space-y-6">
        {/* Results Header */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span className="flex items-center gap-2">
                <CheckCircle className="w-6 h-6 text-green-500" />
                AI批改完成
              </span>
              <div className="flex items-center gap-2">
                <Badge variant="outline">
                  {displayMode === 'coordinates' ? '坐标标注模式' : '局部图卡片模式'}
                </Badge>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleSwitchDisplayMode(
                    displayMode === 'coordinates' ? 'cropped_regions' : 'coordinates'
                  )}
                  disabled={isGrading}
                >
                  {isGrading ? (
                    <Loader2 className="w-4 h-4 animate-spin mr-2" />
                  ) : (
                    displayMode === 'coordinates' ? (
                      <FileText className="w-4 h-4 mr-2" />
                    ) : (
                      <Target className="w-4 h-4 mr-2" />
                    )
                  )}
                  切换到{displayMode === 'coordinates' ? '局部图模式' : '坐标模式'}
                </Button>
              </div>
            </CardTitle>
          </CardHeader>
        </Card>

        {/* Display Results */}
        {displayMode === 'coordinates' && gradingResult.coordinate_annotations ? (
          <CoordinateGradingView
            originalImageUrl={gradingResult.original_image_url || ''}
            annotations={gradingResult.coordinate_annotations}
            gradingSummary={gradingResult.grading_summary}
            knowledgePointSummary={gradingResult.knowledge_point_summary}
          />
        ) : displayMode === 'cropped_regions' && gradingResult.error_cards ? (
          <CroppedRegionGradingView
            originalImageUrl={gradingResult.original_image_url || ''}
            errorCards={gradingResult.error_cards}
            gradingSummary={gradingResult.grading_summary}
            knowledgePointSummary={gradingResult.knowledge_point_summary}
          />
        ) : (
          <Card>
            <CardContent className="p-6 text-center">
              <AlertCircle className="w-12 h-12 mx-auto text-amber-500 mb-4" />
              <h3 className="text-lg font-semibold mb-2">数据加载中...</h3>
              <p className="text-muted-foreground">正在切换显示模式，请稍候</p>
            </CardContent>
          </Card>
        )}

        {/* Action Buttons */}
        <Card>
          <CardContent className="p-4">
            <div className="flex justify-between">
              <Button variant="outline" onClick={() => setCurrentStep('upload')}>
                批改新作业
              </Button>
              <div className="flex gap-2">
                <Button variant="outline">
                  导出批改报告
                </Button>
                <Button>
                  发送给学生
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  };

  return (
    <div className="max-w-6xl mx-auto p-6">
      {currentStep === 'upload' && renderUploadStep()}
      {currentStep === 'grading' && renderGradingStep()}
      {currentStep === 'results' && renderResultsStep()}
    </div>
  );
}